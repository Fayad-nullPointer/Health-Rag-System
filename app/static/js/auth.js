async function register() {

    const username = document.getElementById("reg-username").value;
    const email = document.getElementById("reg-email").value;
    const password = document.getElementById("reg-password").value;
    const country = document.getElementById("reg-country").value;

    const first_name = document.getElementById("reg-firstname").value;
    const last_name = document.getElementById("reg-lastname").value;

    const res = await fetch("/auth/register", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            username,
            email,
            password,
            country,
            first_name,
            last_name
        })
    });

    const data = await res.json();

    if (res.ok) {
        alert("Account created successfully!");
        window.location.href = "/login";
    } else {
        alert(data.detail || "Registration failed");
    }
}


async function login() {

    const username = document.getElementById("login-username").value;
    const password = document.getElementById("login-password").value;

    const res = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
    });

    const data = await res.json();

    console.log("Status:", res.status);
    console.log("Response:", data);

    if (res.ok) {

        localStorage.setItem(
            "token",
            data.access_token
        );

        localStorage.setItem(
            "user",
            JSON.stringify({
                username: data.username,
                full_name: data.full_name
            })
        );

        window.location.href = "/";
    } else {
        alert(data.detail || "Invalid credentials");
    }
}

function getUser() {
    return JSON.parse(localStorage.getItem("user"));
}

function isLoggedIn() {
    return !!getUser();
}

async function logout() {

    try {
        await fetch("/auth/logout", {
            method: "POST"
        });
    } catch (err) {
        console.error(err);
    }

    localStorage.removeItem("user");
    localStorage.removeItem("token");

    window.location.href = "/";
}

function updateNavbar() {
    const user = getUser();

    const login = document.getElementById("login-link");
    const register = document.getElementById("register-link");
    const logoutBtn = document.getElementById("logout-btn");

    if (user) {
        if (login) login.style.display = "none";
        if (register) register.style.display = "none";
        if (logoutBtn) logoutBtn.style.display = "inline-block";
    } else {
        if (login) login.style.display = "inline-block";
        if (register) register.style.display = "inline-block";
        if (logoutBtn) logoutBtn.style.display = "none";
    }
}

document.addEventListener("DOMContentLoaded", updateNavbar);