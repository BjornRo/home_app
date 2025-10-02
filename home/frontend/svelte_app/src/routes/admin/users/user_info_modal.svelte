<script lang="ts" async>
    import type { User } from "$lib/utils/const";
    import { fade } from "svelte/transition";
    import Roles from "./_user_info_cards/roles.svelte";
    import Settings from "./_user_info_cards/settings.svelte";
    import Stats from "./_user_info_cards/stats.svelte";
    import Services from "./_user_info_cards/services.svelte";
    import CloseIcon from "$lib/icons/close_icon.svelte";
    import Modal from "$lib/modal.svelte";

    export let services_list: Array<string>;
    export let user: User | null;
    export let confirm_delete_callback: () => void = () => {};

    const DELETE_MODAL_STATE = { visible: false, ok: false };
    const close_modal = () => (user = null);
    const confirm_delete = () => {
        DELETE_MODAL_STATE.ok = false;
        confirm_delete_callback();
    };
    const on_key_down = (event: KeyboardEvent) => {
        if (event.key === "Escape") {
            if (!DELETE_MODAL_STATE.visible) {
                close_modal();
            }
        }
    };
</script>

<svelte:window on:keydown={on_key_down} />

{#if user}
    <Modal bind:visible={DELETE_MODAL_STATE.visible}>
        <div class="close-modal">
            <div class="confirm-container">
                <input type="checkbox" bind:checked={DELETE_MODAL_STATE.ok} />
                <div class="confirm-text">Confirm</div>
            </div>
            <button class="confirm-btn" disabled={!DELETE_MODAL_STATE.ok} on:click={confirm_delete}>
                Delete: {user.login.name}
            </button>
        </div>
    </Modal>
    <button class="modal-backdrop" on:click={close_modal} />
    <div class="modal-container" transition:fade={{ duration: 200 }}>
        <div class="modal">
            <button class="close-button" on:click={close_modal}>
                <CloseIcon />
            </button>
            <div class="header">
                <p class="header-username">{user.login.name}</p>
                <button
                    class="header-delete-btn"
                    disabled={user === null || user.roles.includes("root")}
                    on:click={() => (DELETE_MODAL_STATE.visible = true)}>Delete user</button
                >
            </div>
            <div class="header-sub">
                <p class="header-userid"><b>UserID</b>: {user.user_id}</p>
                <p class="header-mail"><b>Mail</b>: {user.login.mail ?? "None"}</p>
            </div>
            <div class="cards-container">
                <Stats bind:user />
                <Roles bind:user />
                <Settings bind:user />
                <Services bind:user bind:services_list />
            </div>
        </div>
    </div>
{/if}

<style>
    /* Confirm delete modal */
    .close-modal {
        display: flex;
        flex-direction: column;
        padding: 16px;
        gap: 20px;
        background-color: wheat;
        width: 380px;
    }
    .confirm-container {
        display: flex;
        flex-direction: row;
    }
    .confirm-text {
        font-size: 20px;
        padding: 0;
        margin: 0;
        align-self: center;
    }
    .confirm-btn {
        border: 2px solid #e55656;
        margin: 10px;
        border-radius: 10px;
        padding: 6px;
        cursor: pointer;
        background-color: #be5f5f;
        font-size: 24px;
        color: #363636;
        transition: 0.4s;
    }
    .confirm-btn:hover {
        background-color: rgb(193, 127, 127);
    }
    .confirm-btn:disabled {
        background-color: #848484;
        color: #606060;
        border-color: #363636;
        cursor: not-allowed;
        text-decoration: line-through;
    }
    input[type="checkbox"] {
        /* Transform scale to increase size */
        width: 24px; /* Optional: Set width */
        height: 24px; /* Optional: Set height */
        transform: scale(1.2); /* Adjust scale as needed */
        -ms-transform: scale(1.2); /* IE 9 */
        -moz-transform: scale(1.2); /* Firefox */
        -webkit-transform: scale(1.2); /* Safari and Chrome */
        -o-transform: scale(1.2); /* Opera */
        margin: 10px; /* Optional: Adjust margin to space it out */
    }
    /* END Confirm delete modal */

    .header {
        display: flex;
        flex-direction: row;
        align-items: center;
        gap: 50px;
        margin: 0;
        height: 32px;
        justify-content: space-between;
        margin-right: 200px;
        padding: 0;
    }
    .header-username {
        font-size: 30px;
        color: #363636;
    }
    .header-delete-btn {
        background: #ca4646;
        cursor: pointer;
        font-size: 16px;
        font-weight: bolder;
        padding: 6px;
        border-radius: 10px;
        border: 2px solid rgb(139, 6, 6);
        color: #0f0e0e;
    }
    .header-delete-btn:disabled {
        background: #aaa7a7c6;
        cursor: default;
        color: #9a9a9a;
        text-decoration: line-through;
        border: 2px solid #716e6e;
    }
    .header-delete-btn:not:disabled:hover {
        background: #d27070;
    }
    .header-sub {
        display: flex;
        flex-direction: row;
        padding-top: 10px;
        padding-bottom: 10px;
        gap: 48px;
        align-items: center;
    }
    .header-userid {
        color: #363636;
        margin: 0;
        padding: 0;
        font-size: 16px;
    }
    .header-mail {
        font-size: 16px;
        margin: 0;
        padding: 0;
        color: #363636;
    }
    .cards-container {
        display: flex;
        flex-direction: column;
        gap: 6px;
    }
    .close-button {
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
    .modal-backdrop {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background-color: rgba(0, 0, 0, 0.5);
        z-index: 999;
    }
    .modal-container {
        position: fixed;
        top: 50%;
        left: 50%;
        max-width: calc(var(--global-viewport-width) * 0.95);
        width: 96%;
        transform: translate(-50%, -50%);
        z-index: 1000;
    }
    .modal {
        background: white;
        padding: 0.5rem;
        border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
    }
</style>
