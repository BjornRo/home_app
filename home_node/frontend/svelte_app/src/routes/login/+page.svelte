<script lang="ts">
    import Login from "$lib/widgets/loginform.svelte";
    import { get_creds } from "$lib/utils/func";

    $: logged_in = get_creds();
    let redirect = "/";
</script>

{#if logged_in}
    Already logged in
{:else}
    <Login />
{/if}
