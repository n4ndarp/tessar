//import Cookies from 'https://cdnjs.cloudflare.com/ajax/libs/js-cookie/2.2.1/js.cookie.min.js'
const API_URL = "http://localhost:8000";
const CSRF_URL = `${API_URL}/hehe`;
const LOGIN_URL = `${API_URL}/login`;
const REGISTER_URL = `${API_URL}/register`;
const USER_ME_URL = `${API_URL}/withjwt`;

function callCSRF() {
    fetch(CSRF_URL, {
        method: "GET",
        credentials: 'include'
    })
}

callCSRF();

async function fetchUserInfo() {
    const response = await fetch(USER_ME_URL, {
        method: "GET",
        headers: {
            "Authorization": `Bearer ${localStorage.getItem("access_token")}`
        },
    });

    if (response.ok) {
        const data = await response.json();
        alert(`Welcome, ${data.name}!`);
    } else {
        alert("Failed to fetch user info.");
    }
}

document.getElementById("get-user-info").addEventListener("click", fetchUserInfo);

document.getElementById("login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const username = document.getElementById("login-username").value;
    const password = document.getElementById("login-password").value;
    var tokenz = Cookies.get('csrftoken');
    const response = await fetch(LOGIN_URL, {
        method: "POST",
        body: JSON.stringify({
            username: username,
            password: password
        }),
        headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    });

    if (response.ok) {
        const data = await response.json();
        localStorage.setItem("access_token", data.access_token);
        //localStorage.setItem("refresh_token", data.refresh_token);
        alert("Login successful!");
    } else {
        alert("Login failed!");
    }
});

document.getElementById("register-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const username = document.getElementById("register-username").value;
    const password = document.getElementById("register-password").value;
    const tokenz = Cookies.get('csrftoken');
    const response = await fetch(REGISTER_URL, {
        method: "POST",
        body: JSON.stringify({
            username: username,
            password: password
        }),
        headers: {
            "x-csrftoken": tokenz,
            "Content-type": "application/json; charset=UTF-8",
        }
    });

    if (response.ok) {
        const data = await response.json();
        alert(`Registered successfully!`);
    } else {
        alert("Registration failed!");
    }
});

function logout() {
    if (localStorage.getItem("access_token")) {
        localStorage.clear(); 
        alert("Logged out.");
    }   
    else{
        alert("You're not logged in!");
    }
}

document.getElementById("logout").addEventListener("click", logout);  