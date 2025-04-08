<script lang="ts">
    import { fade, fly } from "svelte/transition";
    import Success from "$lib/icons/success.svelte";
    import Error from "$lib/icons/error.svelte";
    import Info from "$lib/icons/info.svelte";
    import Close from "$lib/icons/close.svelte";
    import { toast, ToastType, type Notification } from "./toast_notification.svelte";

    export let data: Notification;
    export let dismissible = true;
</script>

<article class={data.type} role="alert" in:fly={{ x: 200 }} out:fly={{ x: 200 }}>
    {#if data.type === ToastType.SUCCESS}
        <Success width="1.1em" />
    {:else if data.type === ToastType.ERROR}
        <Error width="1.1em" />
    {:else}
        <Info width="1.1em" />
    {/if}

    <div class="text">
        {data.text}
    </div>

    {#if dismissible}
        <button class="close" on:click={() => toast.dismiss(data.id)}>
            <Close width="0.8em" />
        </button>
    {/if}
</article>

<style>
    article {
        display: flex;
        pointer-events: all;
        color: #ffffff;
        padding: 0.75rem 1.5rem;
        border-radius: 0.4rem;
        width: 14rem;
        box-shadow: 0 0 8px #136380a3;
    }
    .error {
        background: IndianRed;
    }
    .success {
        background: MediumSeaGreen;
    }
    .info {
        background: #2590ba;
    }
    .text {
        margin-left: 1rem;
    }
    button {
        color: white;
        cursor: pointer;
        background: transparent;
        border: 0 none;
        padding: 0;
        margin: 0 0 0 auto;
        line-height: 1;
        font-size: 1rem;
    }
</style>
