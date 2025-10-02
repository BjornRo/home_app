<script lang="ts">
    import { get } from "svelte/store";
    import { credentials } from "$lib/utils/stores";
    import { get_creds } from "$lib/utils/func";
    import Login from "$lib/widgets/loginform.svelte";

    let show: boolean = false;
    let dialog: HTMLDialogElement;
    $: logged_in = get_creds();
    $: if (dialog && show) dialog.showModal();
</script>

{#if !logged_in}
    <button class="btn login-btn log-btn" on:click={() => (show = true)}>Login</button>
    <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-noninteractive-element-interactions -->
    <dialog bind:this={dialog} on:close={() => (show = false)} on:click|self={() => dialog.close()}>
        <Login />
    </dialog>
    <style>
        dialog {
            background: none;
            border: none;
            padding: 0;
        }
        dialog::backdrop {
            background: rgba(0, 0, 0, 0.5);
        }
        dialog[open] {
            animation: zoom 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
        }
        @keyframes zoom {
            from {
                transform: scale(0.8);
            }
            to {
                transform: scale(1);
            }
        }
        dialog[open]::backdrop {
            animation: fade 0.3s ease-out;
        }
        @keyframes fade {
            from {
                opacity: 0;
            }
            to {
                opacity: 1;
            }
        }
    </style>
{:else}
    <button class="btn settings-btn"
        >User:<br />
        <div class="name">{get(credentials)?.data.name}</div>
    </button>
    <form method="POST" action="/login?/logout" class="fill">
        <button class="btn logout-btn log-btn">Logout</button>
    </form>
{/if}

<style>
    .name {
        font-size: 15px;
    }
    .fill {
        display: flex;
    }
    .login-btn {
        background-color: #30b0c1;
    }
    .logout-btn {
        background-color: #c81e92a5;
    }
    .settings-btn {
        background-color: rgb(179, 138, 88);
        font-size: 14px;
        width: 150px;
    }
    .log-btn {
        font-size: 16px;
        width: 100px;
    }
    .btn {
        cursor: pointer;
        box-sizing: border-box;
        font-family: Arial, Helvetica, sans-serif;
        color: white;
        font-weight: bold;
        margin: 8px;
        margin-right: 6px;
        box-shadow: #30b0c1;
        border: none;
        border-radius: 14px;
        text-align: center;
        box-shadow: 0 0 10px rgba(45, 64, 73, 0.563);
        transition: background-color 0.2s ease, border-radius 0.5s ease;
    }

    .btn:hover {
        background-color: #3689949b;
        border-radius: 18px;
    }
</style>
