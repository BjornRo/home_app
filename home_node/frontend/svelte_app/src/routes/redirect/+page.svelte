<script lang="ts" async>
    import { page } from "$app/stores";
    import { credentials } from "$lib/utils/stores";
    import { get } from "svelte/store";
    import type { PageData } from "./$types";
    import { TOKEN_PATH, type UserData } from "$lib/utils/const";
    import { api_fetch } from "$lib/utils/func";
    import { error, redirect } from "@sveltejs/kit";
    import { onMount } from "svelte";
    import { goto } from "$app/navigation";

    export let data: PageData;

    const fetch_decode_set_creds_cookieSt = async (): Promise<boolean> => {
        const token_expiry_resp = await api_fetch(TOKEN_PATH);
        if (!token_expiry_resp.ok) {
            return false;
        }
        const data_resp = await api_fetch("user/self/data");
        if (!data_resp.ok) {
            error(500, "should not happen? :(");
        }
        credentials.set({
            data: (await data_resp.json()) as UserData,
            token_expiry: parseInt(await token_expiry_resp.text(), 10),
        });
        return true;
    };

    onMount(async () => {
        if (get(credentials) && !data.credentials) {
            if (await fetch_decode_set_creds_cookieSt()) {
                window.location.reload();
            }
        }
        const value = $page.url.searchParams.get("to") ?? "/";
        redirect(307, value === "/" ? value : `/${value}`);
    });
</script>

redirect
