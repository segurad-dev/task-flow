function authApp() {
  return {
    mode: "login",      // 'login' | 'register'
    email: "",
    username: "",
    password: "",
    loading: false,
    error: "",

    // Called once by Alpine when the component is initialised.
    // If a token already exists we skip the auth form entirely.
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
          // Store username for display; the real user object comes in commit 5
          localStorage.setItem("username", this.email.split("@")[0]);
          this.$dispatch("authenticated");
        } else {
          await register(this.email, this.username, this.password);
          // After registration switch to login and prefill email
          this.mode = "login";
          this.password = "";
          this.error = "";
        }
      } catch (e) {
        this.error = e.message;
      } finally {
        this.loading = false;
      }
    },
  };
}
