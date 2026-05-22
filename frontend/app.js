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

    init() {
      this.username = localStorage.getItem("username") || "Пользователь";
    },

    logout() {
      localStorage.clear();
      this.$dispatch("logout");
    },
  };
}
