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

    // Tasks state (populated in commit 7)
    tasks: [],
    statusFilter: "all",
    tasksLoading: false,

    // Create task form state (populated in commit 8)
    showNewTaskForm: false,
    newTask: { title: "", description: "" },
    taskSaving: false,

    // Analytics state (populated in commit 10)
    analytics: null,

    async init() {
      this.username = localStorage.getItem("username") || "Пользователь";
      await this.loadProjects();
    },

    logout() {
      localStorage.clear();
      this.$dispatch("logout");
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
        console.error("loadProjects:", e.message);
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
      await this.loadTasks();
    },

    // ── Tasks ─────────────────────────────────────────────────────────────

    async loadTasks() {
      if (!this.currentProject) return;
      this.tasksLoading = true;
      try {
        // API returns tasks assigned to current user; filter by project client-side
        const all = await getTasks();
        this.tasks = all.filter(t => t.project_id === this.currentProject.id);
      } catch (e) {
        console.error("loadTasks:", e.message);
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
        console.error("createProject:", e.message);
      }
    },
  };
}
