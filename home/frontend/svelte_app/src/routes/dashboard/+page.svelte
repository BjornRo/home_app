<script lang="ts">
    import { onMount } from "svelte";
    onMount(() => {
        //const val = verify_token(token, Keys.access);
    });

    let visible = true;
</script>

<button on:click={() => (visible = true)}> show modal </button>
Dash bård

<style>
    button {
        height: 30px;
    }
</style>
