<script lang="ts">
    import type { LayoutData } from "./$types";
    import { page } from "$app/stores";

    export let data: LayoutData;

    $: route_id = $page.route.id as string;
</script>

<div class="main-grid">
    <div class="sidebg" />
    <div class="sidebar">
        <a href="/admin" class={route_id === "/admin" ? "active" : ""}>Home</a>
        {#each data.sidebar_items as { key, value }}
            <a href={value} class={route_id.startsWith(value) ? "active" : ""}>
                {key}
            </a>
        {/each}
    </div>
    <div class="content">
        <slot />
    </div>
</div>

<style>
    :root {
        --sidebar-width: 140px;
    }

    .sidebg {
        z-index: -1;
        position: fixed;
        left: 0;
        top: 0;
        height: 100%;
        background-color: #bfbebe36;
        width: var(--sidebar-width);
        border: orange 2px solid;
    }
    .main-grid {
        display: grid;
        justify-items: stretch;
        align-items: stretch;
        grid-template-columns: var(--sidebar-width) 1fr;
    }

    .content {
        height: 100%;
        padding: 0px;
        /* margin-left: var(--sidebar-width); */
    }

    .sidebar {
        z-index: 1;
        height: fit-content;
        width: var(--sidebar-width);
        background-color: #21ec6836;
        border: red 2px solid;
    }

    .sidebar a {
        border-bottom: #7272722f 2px solid;
        border-left: 50px solid transparent;
        border-right: 50px solid transparent;
        display: flex;
        justify-content: center;
        text-align: center;
        font-weight: bold;
        font-family: Arial, sans-serif;
        color: black;
        padding: 14px;
        text-decoration: none;
        transition: background-color 0.2s ease, border-radius 0.5s ease;
    }
    .sidebar a.active {
        background-color: #7cccae;
        color: white;
    }
    .sidebar a:hover:not(.active) {
        background-color: #20f36a36;
    }
    .sidebar a:hover {
        background-color: #20f36a36;
    }
</style>
