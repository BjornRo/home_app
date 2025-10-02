<script lang="ts">
    import type { LayoutData } from "./$types";
    import Navbar from "$lib/navbar.svelte";
    import { beforeNavigate } from "$app/navigation";
    import { get } from "svelte/store";
    import { credentials, is_mobile_view } from "$lib/utils/stores";
    import { is_expired } from "$lib/utils/token";
    import { api_fetch } from "$lib/utils/func";
    import { MOBILE_WIDTH, TOKEN_PATH } from "$lib/utils/const";
    import ToastNotify from "$lib/toast_notification.svelte";

    export let data: LayoutData;

    is_mobile_view.set(window.innerWidth <= MOBILE_WIDTH);
    const update_mobile_view_state = () => {
        if (window.innerWidth <= MOBILE_WIDTH) {
            if (!get(is_mobile_view)) {
                is_mobile_view.set(true);
            }
        } else if (get(is_mobile_view)) {
            is_mobile_view.set(false);
        }
    };

    beforeNavigate(async ({ to, cancel }) => {
        let creds = get(credentials);
        if (creds && is_expired(creds.token_expiry, 10)) {
            const res = await api_fetch(TOKEN_PATH);
            creds = res.ok
                ? {
                      data: creds.data,
                      token_expiry: parseInt(await res.text(), 10),
                  }
                : null;
            credentials.set(creds);
        }
    });
</script>

<svelte:window on:resize={update_mobile_view_state} />
<ToastNotify />

<div class="viewport-bg">
    <div class="viewport vpstyle">
        <Navbar navbar_items={data.navbar_items} />
        <div class="layout">
            <slot />
        </div>
    </div>
</div>
<svelte:head>
    <style>
        :root {
            --global-viewport-width: 1200px;
        }
        @media (min-width: 1200px) {
            .viewport {
                width: var(--global-viewport-width);
            }
        }
        .viewport {
            display: flex;
            flex-direction: column;
            align-items: stretch;
            /* width: 1000px; */
            margin: 0;
            padding: 0;
        }

        body {
            font-family: Verdana, Arial, sans-serif;
        }
    </style>
</svelte:head>

<style>
    .layout {
        display: flex;
        align-items: stretch;
        height: 100%;
        width: 100%;
    }
    .vpstyle {
        margin: auto;
        background-color: rgb(90, 113, 118);
        height: 100vh;
    }
    .viewport-bg {
        width: 100vi;
        height: 100vh;
        background-color: rgb(117, 151, 152);
    }
</style>
