<script lang="ts">
    import { fade } from "svelte/transition";
    import CloseIcon from "$lib/icons/close_icon.svelte";

    export let visible: boolean;

    let dialog: HTMLDialogElement;

    $: if (dialog && visible) dialog.showModal();
</script>

{#if visible}
    <span class="backdrop" transition:fade={{ duration: 200 }} />
{/if}
<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-noninteractive-element-interactions -->
<dialog bind:this={dialog} on:close={() => (visible = false)} on:click|self={() => dialog.close()}>
    <!-- svelte-ignore a11y-autofocus -->
    <button autofocus on:click={() => dialog.close()}>
        <CloseIcon />
    </button>
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    {#if visible}
        <div on:click|stopPropagation transition:fade={{ duration: 300 }}>
            <slot />
        </div>
    {/if}
</dialog>

<style>
    button {
        display: block;
        background: none;
        position: absolute;
        top: 10px;
        right: 10px;
        margin: 0;
        padding: 0;
        cursor: pointer;
        outline: 0;
        border: none;
        transition: 0.3s;
    }

    dialog {
        width: fit-content;
        height: fit-content;
        background: 0;
        border: 0;
        outline: 0;
        padding: 0;
        overflow: hidden;
        border-radius: 14px;
    }
    dialog[open] {
        animation: zoom 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
    }
    @keyframes zoom {
        from {
            transform: scale(0.9);
        }
        to {
            transform: scale(1);
        }
    }
    dialog[open]::backdrop {
        animation: fade 0.2s ease-out;
    }
    @keyframes fade {
        from {
            opacity: 0;
        }
        to {
            opacity: 1;
        }
    }
    .backdrop {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: #0000006b;
        z-index: 1001;
    }
</style>
