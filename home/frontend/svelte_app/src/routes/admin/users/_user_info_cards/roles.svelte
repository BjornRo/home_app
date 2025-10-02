<script lang="ts">
    import type { User } from "$lib/utils/const";
    import { HTTP_METHOD, RolesEnum } from "$lib/utils/const";
    import { check_creds_then_fetch } from "$lib/utils/func";
    import { fade } from "svelte/transition";
    import { InfoPopup } from "$lib/utils/ui-state";

    export let user: User;
    let all_roles: RolesEnum[] = Object.values(RolesEnum);
    const get_available_roles = () => all_roles.filter((e) => !user.roles.includes(e));
    let available_roles = get_available_roles();

    let confirmation_popup = new InfoPopup<RolesEnum>();

    const swap_btn_click = (role: RolesEnum) => (confirmation_popup = confirmation_popup.set_value(role));
    const request_swap_role = async (new_role: RolesEnum) => {
        if (!confirmation_popup.consent_given) {
            alert("Consent not given");
            return;
        }
        const old_role = user.roles[0];
        if (old_role === new_role) {
            alert("Old and new role is the same");
            return;
        }
        confirmation_popup = confirmation_popup.off();
        const defer = () => {
            confirmation_popup = confirmation_popup.on();
        };

        const resp = await check_creds_then_fetch(
            `user/${user.user_id}/role/${new_role}?replace_role=${old_role}`,
            HTTP_METHOD.PATCH
        );
        if (resp.ok) {
            user.roles[0] = new_role;
            available_roles = get_available_roles();
            user = user;
        } else {
            alert(JSON.stringify(await resp.json()));
        }
        defer();
    };
    const close_confirm_box = (event: MouseEvent) => {
        if (confirmation_popup.value !== null) {
            const tag = event.target as HTMLElement | null;
            if (tag) {
                const ignore =
                    (tag instanceof HTMLButtonElement && tag.classList.contains("swap-role-btn")) ||
                    confirm_box.contains(tag);
                if (!ignore) {
                    confirmation_popup = confirmation_popup.set_value(null);
                }
            }
        }
    };
    let confirm_box: HTMLDivElement;
</script>

<svelte:window on:click={close_confirm_box} />

<div class="main">
    <div class="header">
        <p>Roles</p>
        <span>Current role: <b>{user.roles[0]}</b></span>
    </div>
    <div class="content">
        {#each available_roles as role}
            <div class="role-container">
                <button class="swap-role-btn" on:click={() => swap_btn_click(role)}>
                    {role}
                </button>
                {#if confirmation_popup.value === role}
                    <div id="confirm-box" transition:fade={{ duration: 150 }} bind:this={confirm_box}>
                        <div class="confirm-container">
                            Swap to
                            <label>
                                <input
                                    type="checkbox"
                                    bind:checked={confirmation_popup.consent_given}
                                    id={role.toString()}
                                />
                            </label>
                        </div>
                        <button
                            class="confirm-btn {confirmation_popup.consent_given ? 'ok' : ''}"
                            disabled={!confirmation_popup.consent_given}
                            on:click={async () => await request_swap_role(role)}
                        >
                            Confirm
                        </button>
                    </div>
                {/if}
            </div>
        {/each}
    </div>
</div>

<style>
    p {
        margin: 4px;
        margin-bottom: 0px;
        font-size: 20px;
        padding: 0;
    }
    label {
        display: inline-block;
        padding: 5px;
    }

    b {
        color: #c820c2;
    }
    .confirm-container {
        display: flex;
        white-space: nowrap;
        align-items: center;
        font-size: 16px;
    }
    span {
        align-self: flex-end;
        font-size: 16px;
        margin-left: 24px;
    }
    .main {
        border: 3px solid #86a528;
        border-radius: 6px;
        background-color: #dfe5de;
        display: flex;
        flex-direction: column;
        flex-wrap: wrap;
    }
    .header {
        display: flex;
        flex-direction: row;
    }
    .content {
        display: flex;
        flex-direction: row;
        margin: 4px;
        display: flex;
        align-items: stretch;
        border-radius: 4px;
        border: 2px solid #40a932de;
        box-shadow: inset 0 0 4px #792a2a80;
    }
    .role-container {
        display: flex;
        height: 56px;
    }
    .swap-role-btn {
        cursor: pointer;
        border: #cb775b 2px solid;
        background: none;
        margin: 5px;
        margin-right: 3px;
        font-size: 22px;
        font-weight: bolder;
        width: 100px;
        border-radius: 6px;
    }
    .swap-role-btn:hover {
        background: #7e00001d;
        transition: 0.2s;
    }
    #confirm-box {
        display: flex;
        flex-direction: column;
        background: #fff;
        border: #cb775b 2px solid;
        position: absolute;
        border-radius: 6px;
        padding: 8px;
        margin-left: -2px;
        margin-top: 54px;
        width: 92px;
        transition: height 2s ease;
        box-shadow: 0 4px 8px #0000001a;
    }
    .confirm-btn {
        margin-top: 10px;
        padding: 5px;
        background-color: #9c939c;
        border: none;
        color: white;
        font-size: 16px;
        border-radius: 4px;
    }

    .confirm-btn.ok {
        background-color: green;
        cursor: pointer;
        transition: 0.3s;
    }
</style>
