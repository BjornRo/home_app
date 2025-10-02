<script lang="ts">
    import { page } from "$app/stores";
    import User from "$lib/icons/user_icon.svelte";

    const sidebar_state_key = "asbexp";

    let exp = localStorage.getItem(sidebar_state_key) === "1";
    const toggle_sidebar = () => {
        exp = !exp;
        localStorage.setItem(sidebar_state_key, exp ? "1" : "0");
    };
</script>

<div class="main">
    <div class="navbar">
        <button class="hamburger" on:click={toggle_sidebar}>&#9776;</button>
        <div class="navbar-title">Admin</div>
    </div>
    <div class="viewport">
        <div class="sidebar" class:expanded={exp}>
            <a href="/admin" class="sidebar-item">
                <i class="icon">🏠</i>
                <span class="text">Home</span>
            </a>
            <a href="/admin/users" class="sidebar-item">
                <i class="icon">👤</i>
                <span class="text">Users</span>
            </a>
            <!-- svelte-ignore a11y-invalid-attribute -->
            <a href="#" class="sidebar-item">
                <i class="icon">🔍</i>
                <span class="text">Search</span>
            </a><!-- svelte-ignore a11y-invalid-attribute -->
            <a href="#" class="sidebar-item">
                <i class="icon">⚙️</i>
                <span class="text">Settings</span>
            </a>
            <!-- svelte-ignore a11y-invalid-attribute -->
            <a href="#" class="sidebar-item">
                <i class="icon">📧</i>
                <span class="text">Contact</span>
            </a>
        </div>

        <div class="content">
            <slot />
        </div>
    </div>
</div>

<style>
    .content {
        display: flex;
        align-items: stretch;
        height: 100%;
        width: 100%;
        /* Allow content to take up remaining space */
        flex-grow: 1;
        /* Enable vertical scrolling */
        overflow-y: auto;
    }
    .main {
        display: flex;
        align-items: stretch;
        flex-direction: column;
        width: 100%;
        height: 100%;
    }

    .navbar {
        display: flex;
        height: 50px;
        width: 100%;
        justify-content: flex-start;
        align-items: stretch;
        background-color: #535353;
        color: white;
        /* flex-direction: row; */
        gap: 10px;
    }

    .navbar-title {
        margin: auto;
        margin-left: 12px;
        font-size: 26px;
    }

    .hamburger {
        cursor: pointer;
        align-content: center;
        text-align: center;
        font-size: 25px;
        transform: scaleX(1.2) scaleY(1);
        transform-origin: left;
        background: none;
        color: #bbbbbb;
        margin-left: 8px;
        border-radius: 6px;
        padding: 4px;
        padding-top: 1px;
        margin-top: 4px;
        margin-bottom: 4px;
        border: rgb(125, 125, 125) 3px solid;
    }

    .viewport {
        display: flex;
        flex-direction: row;
        width: 100%;
        height: 100%;
        align-items: stretch;
    }

    .sidebar {
        display: flex;
        flex-direction: column;
        width: 60px;
        height: 100%;
        background-color: #464646;
        transition: width 0.3s;
    }

    .sidebar.expanded {
        width: 200px;
    }

    .sidebar-item {
        display: flex;
        align-items: center;
        flex-shrink: 0;
        padding: 14px;
        color: white;
        text-decoration: none;
        transition: background-color 0.3s;
    }

    .sidebar-item:hover {
        background-color: #555;
    }

    .sidebar-item .icon {
        font-size: 1.5em;
    }

    .sidebar-item .text {
        margin-left: 20px;
        display: none;
    }

    .sidebar.expanded .sidebar-item .text {
        display: inline-block;
    }
</style>
