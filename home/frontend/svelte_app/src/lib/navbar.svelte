<script lang="ts">
    import { page } from "$app/stores";
    import Loginmodal from "$lib/loginmodal.svelte";
    import { type KeyValueItem } from "$lib/utils/const";
    export let navbar_items: KeyValueItem[];
    navbar_items = [{ key: "Dashboard", value: "/dashboard" }, ...navbar_items];
    $: route_id = $page.route.id!;
</script>

<div class="navbar">
    <a href="/" class="logo">B</a>
    <div class="nav-menu">
        {#each navbar_items as { key, value }}
            <a href={value} class="nav-item {route_id.startsWith(value) ? 'active' : ''}" data-sveltekit-reload>
                {key}
            </a>
        {/each}
    </div>
    <Loginmodal />
</div>

<style>
    :root {
        --navbar-height: 80px;
        --navbar-item-width: 120px;

        --logo-height: 85%;
    }
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }

    a {
        text-decoration: none;
    }

    .logo {
        display: flex;
        justify-content: center;
        padding-top: 4px;
        padding-left: 2px;
        font-size: 44px;
        margin: auto;
        margin-left: 8px;
        background: #0843b9c4;
        border-radius: 50%;
        height: var(--logo-height);
        color: #d9d9d9;
        aspect-ratio: 1;
        border: 2px solid rgba(3, 0, 97, 0.359);
        transition:
            background-color 0.2s ease,
            border-radius 0.5s ease;
    }

    .logo:hover {
        background-color: #3763bcc4;
    }

    .nav-menu {
        display: flex;
        width: 100%;
        height: 100%;
        align-items: stretch;
        margin: auto;
        margin-left: 10px;
        transition: display 2s ease;
    }

    .nav-item {
        display: flex;
        justify-content: center;
        margin: 10px;
        margin-right: 0px;
        align-items: center;
        font-size: 18px;
        width: var(--navbar-item-width);
        border-radius: 12px;
        color: rgba(255, 255, 255, 0.988);
        background-color: #ffffff2b;
        font-family: Verdana, Geneva, Tahoma, sans-serif;
        box-shadow: 0 0 4px 0 rgba(0, 0, 0, 0.2);
        transition:
            background-color 0.2s ease,
            border-radius 0.5s ease;
    }

    .nav-item:hover {
        background-color: rgba(255, 255, 255, 0.141);
        border-radius: 16px;
    }

    .active {
        background-color: #7bd3d399;
        text-decoration: underline solid 2px #2da12f;
        text-underline-offset: 2px;
    }

    .active:hover {
        background-color: #3da4b4;
    }

    .navbar {
        display: flex;
        width: 100%;
        flex-direction: row;
        background-color: #7d7d7d;
        height: var(--navbar-height);
        align-items: stretch;
        justify-content: center;
    }
</style>
