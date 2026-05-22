// ── Auth component ────────────────────────────────────────────────────────────

function authApp() {
  return {
    mode: "login",      // 'login' | 'register'
    email: "",
    username: "",
    password: "",
    loading: false,
    error: "",

    init() {
      if (localStorage.getItem("token")) {
        this.$dispatch("authenticated");
      }
    },

    switchMode(m) {
      this.mode = m;
      this.error = "";
    },

    async submit() {
      this.error = "";
      this.loading = true;
      try {
        if (this.mode === "login") {
          const data = await login(this.email, this.password);
          localStorage.setItem("token", data.access_token);
          localStorage.setItem("username", this.email.split("@")[0]);
          this.$dispatch("authenticated");
        } else {
          await register(this.email, this.username, this.password);
          // After registration switch to login with email prefilled
          this.mode = "login";
          this.password = "";
        }
      } catch (e) {
        this.error = e.message;
      } finally {
        this.loading = false;
      }
    },
  };
}

// ── Dashboard component ───────────────────────────────────────────────────────

function dashboardApp() {
  return {
    username: "",

    // Projects state (populated in commit 6)
    projects: [],
    currentProject: null,
    showNewProjectForm: false,
    newProjectTitle: "",
    projectsLoading: false,

    currentUserId: null,

    // Tasks state
    tasks: [],
    statusFilter: "all",
    tasksLoading: false,

    // Create task form
    showNewTaskForm: false,
    newTask: { title: "", description: "" },
    taskSaving: false,

    // Analytics state
    analytics: null,

    // Toast notification
    toastMessage: "",
    toastVisible: false,
    _toastTimer: null,

    async init() {
      this.username = localStorage.getItem("username") || "Пользователь";
      // Decode user_id from the JWT payload (field "sub") — no extra API call needed
      try {
        const token = localStorage.getItem("token");
        const payload = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
        this.currentUserId = parseInt(payload.sub);
      } catch {
        this.currentUserId = null;
      }
      await this.loadProjects();
    },

    logout() {
      localStorage.clear();
      this.$dispatch("logout");
    },

    showToast(message) {
      clearTimeout(this._toastTimer);
      this.toastMessage = message;
      this.toastVisible = true;
      this._toastTimer = setTimeout(() => { this.toastVisible = false; }, 3000);
    },

    // ── Projects ──────────────────────────────────────────────────────────

    async loadProjects() {
      this.projectsLoading = true;
      try {
        this.projects = await getProjects();
        // Auto-select first project if none selected
        if (!this.currentProject && this.projects.length > 0) {
          await this.selectProject(this.projects[0]);
        }
      } catch (e) {
        this.showToast(e.message);
      } finally {
        this.projectsLoading = false;
      }
    },

    async selectProject(project) {
      this.currentProject = project;
      this.tasks = [];
      this.analytics = null;
      this.showNewTaskForm = false;
      this.statusFilter = "all";
      await Promise.all([this.loadTasks(), this.loadAnalytics()]);
    },

    // ── Analytics ─────────────────────────────────────────────────────────

    async loadAnalytics() {
      if (!this.currentProject) return;
      try {
        this.analytics = await getProjectAnalytics(this.currentProject.id);
      } catch (e) {
        this.showToast(e.message);
      }
    },

    // ── Tasks ─────────────────────────────────────────────────────────────

    async loadTasks() {
      if (!this.currentProject) return;
      this.tasksLoading = true;
      try {
        // Pass project_id so the API returns all tasks in the project
        this.tasks = await getTasks(this.currentProject.id);
      } catch (e) {
        this.showToast(e.message);
      } finally {
        this.tasksLoading = false;
      }
    },

    get filteredTasks() {
      if (this.statusFilter === "all") return this.tasks;
      return this.tasks.filter(t => t.status === this.statusFilter);
    },

    statusLabel(status) {
      return { todo: "Ожидает", in_progress: "В работе", done: "Готово", cancelled: "Отменено" }[status] ?? status;
    },

    async changeStatus(taskId, newStatus) {
      try {
        const updated = await updateTask(taskId, { status: newStatus });
        // Update in-place so the list doesn't flicker with a full reload
        const idx = this.tasks.findIndex(t => t.id === taskId);
        if (idx !== -1) this.tasks[idx] = updated;
      } catch (e) {
        this.showToast(e.message);
      }
    },

    async removeTask(taskId) {
      if (!confirm("Удалить задачу?")) return;
      try {
        await deleteTask(taskId);
        this.tasks = this.tasks.filter(t => t.id !== taskId);
      } catch (e) {
        this.showToast(e.message);
      }
    },

    async submitNewTask() {
      const title = this.newTask.title.trim();
      if (!title || !this.currentProject) return;
      this.taskSaving = true;
      try {
        await createTask(title, this.newTask.description, this.currentProject.id, this.currentUserId);
        this.newTask = { title: "", description: "" };
        this.showNewTaskForm = false;
        await this.loadTasks();
      } catch (e) {
        this.showToast(e.message);
      } finally {
        this.taskSaving = false;
      }
    },

    statusBadgeClass(status) {
      return {
        todo:        "bg-gray-100 text-gray-600",
        in_progress: "bg-blue-100 text-blue-700",
        done:        "bg-green-100 text-green-700",
        cancelled:   "bg-red-100 text-red-600",
      }[status] ?? "bg-gray-100 text-gray-600";
    },

    async submitNewProject() {
      const title = this.newProjectTitle.trim();
      if (!title) return;
      try {
        const project = await createProject(title);
        this.projects.push(project);
        await this.selectProject(project);
        this.newProjectTitle = "";
        this.showNewProjectForm = false;
      } catch (e) {
        this.showToast(e.message);
      }
    },
  };
}
