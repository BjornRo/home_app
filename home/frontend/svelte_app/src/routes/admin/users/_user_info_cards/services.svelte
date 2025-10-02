<script lang="ts">
    import { HTTP_METHOD, RolesEnum, type User } from "$lib/utils/const";
    import { Checkbox, InfoPopup } from "$lib/utils/ui-state";
    import { check_creds_then_fetch, rwx_num_to_str, contains } from "$lib/utils/func";
    import { fade } from "svelte/transition";

    enum Method {
        ADD = "add",
        DEL = "del",
        UPD = "ok",
    }

    const get_available_services = () => {
        const user_services = user.acl.map((e) => e.resource);
        return services_list.filter((e) => !user_services.includes(e));
    };

    const service_popup_click = (service_name: string, rwx: number) => {
        confirm_popup = confirm_popup.set_value(service_name);
        if (confirm_popup.value !== null) {
            rwx_display = reset_rwx_display(rwx);
        }
        validate_input();
    };

    const validate_input = () => {
        let all_values_off = true;
        let modified_value = false;
        for (const input of Object.values(rwx_display)) {
            if (input.value) {
                all_values_off = false;
            }
            if (!input.is_default()) {
                modified_value = true;
            }
            if (!all_values_off && modified_value) {
                break;
            }
        }
        valid_input_add = !all_values_off;
        valid_input = all_values_off || modified_value;
        if (user && !valid_input) {
            confirm_popup.consent_given = false;
        }
        if (rwx_values_off !== all_values_off) {
            confirm_popup.consent_given = false;
        }
        rwx_values_off = all_values_off;
    };

    const rwx_value = (): number =>
        parseInt(
            Object.values(rwx_display)
                .map((e) => (e.value ? "1" : "0"))
                .join(""),
            2
        );

    const rwx_num_to_bools = (rwx: number) =>
        rwx
            .toString(2)
            .padStart(3, "0")
            .split("")
            .map((b) => b === "1") as [boolean, boolean, boolean];

    const reset_rwx_display = (rwx: number) => {
        const [r, w, x] = rwx_num_to_bools(rwx);
        rwx_display.r.reset(r);
        rwx_display.w.reset(w);
        rwx_display.x.reset(x);
        return rwx_display;
    };

    const request_update_service = async (method: Method) => {
        return;
        let old_role = user.roles[0];
        if (!confirmed_swap || old_role == new_role) {
            return;
        }
        confirmed_swap = false;
        locked_box = true;

        const resp = await check_creds_then_fetch(
            `user/${user.user_id}/role/${new_role}?replace_role=${old_role}`,
            HTTP_METHOD.PATCH
        );
        if (!resp.ok) {
            const data = await resp.json();
            alert(JSON.stringify(data));
            locked_box = false;
            return;
        }
        user.roles[0] = new_role;
        user = user;
        available_roles = get_available_roles();
        selected_index = null;
        locked_box = false;
    };
    const get_rwx_keys = () => Object.keys(rwx_display) as RWXKey[];

    const on_window_click = (event: MouseEvent) => {
        const ignore_parent = ["update-access-btn", "add-access-btn", "confirm-box"];
        const tag = event.target as HTMLElement | null;
        if (confirm_popup.value !== null && tag) {
            if (!contains(tag, ignore_parent)) {
                valid_input = false;
                confirm_popup = confirm_popup.set_value(null);
            }
        }
    };
    export let user: User;
    export let services_list: string[];

    // Testing
    // services_list = ["store", "photo", "notes"];
    // user.acl = [
    //     { resource: "foo", rwx: 1 },
    //     { resource: "bar", rwx: 2 },
    // ];

    let rwx_display = { r: new Checkbox(false, "r"), w: new Checkbox(false, "w"), x: new Checkbox(false, "x") };

    type RWXKey = keyof typeof rwx_display;
    let confirm_popup = new InfoPopup<string>();
    let valid_input: boolean = false;
    let valid_input_add: boolean = false;
    let rwx_values_off: boolean = false;

    let available_services = get_available_services();
    $: ok_to_send = confirm_popup.consent_given && valid_input;
    $: ok_to_add = confirm_popup.consent_given && valid_input_add;
</script>

<svelte:window on:click={on_window_click} />

{#if services_list.length !== 0 || user.acl.length !== 0}
    <div class="main">
        <div class="header">Services ACL</div>
        <div class="top-content"><span>User access</span></div>
        <div class="content">
            {#if user.acl.length !== 0}
                {#each user.acl as acl}
                    <div class="service-container">
                        <button class="update-access-btn" on:click={() => service_popup_click(acl.resource, acl.rwx)}>
                            <span class="item margin">
                                <span class="item">
                                    <span class="item-header">Name</span>
                                    <span class="item-footer">{acl.resource}</span>
                                </span>
                                <span class="item">
                                    <span class="item-header">Access</span>
                                    <span class="item-footer rwx">{rwx_num_to_str(acl.rwx)}</span>
                                </span>
                            </span>
                        </button>
                        {#if confirm_popup.value === acl.resource}
                            <div class="confirm-box upper" transition:fade={{ duration: 150 }}>
                                <div class="rwx-container">
                                    {#each get_rwx_keys() as k}
                                        <div class="rwx-display">
                                            <div class="rwx-display-text">{rwx_display[k].value ? k : "-"}</div>
                                            <input
                                                type="checkbox"
                                                class="rwx-checkbox"
                                                bind:checked={rwx_display[k].value}
                                                on:change={() => validate_input()}
                                            />
                                        </div>
                                    {/each}
                                </div>
                                <div class="confirm-container">
                                    {rwx_values_off ? "Delete" : "Update"}
                                    <label>
                                        <input
                                            type="checkbox"
                                            bind:checked={confirm_popup.consent_given}
                                            disabled={!valid_input}
                                        />
                                    </label>
                                </div>
                                <button
                                    class="confirm-btn {ok_to_send ? (rwx_values_off ? Method.DEL : Method.UPD) : ''}"
                                    disabled={!ok_to_send}
                                    on:click={async () =>
                                        await request_update_service(rwx_values_off ? Method.DEL : Method.UPD)}
                                >
                                    {rwx_values_off ? "Delete" : "Update"}
                                </button>
                            </div>
                        {/if}
                    </div>
                {/each}
            {:else}
                <p>Empty</p>
            {/if}
        </div>
        <div class="top-content"><span>Available services</span></div>
        <div class="content">
            {#if available_services.length === 0}
                <p>Empty</p>
            {:else}
                {#each available_services as service}
                    <div class="service-container">
                        <button class="add-access-btn" on:click={() => service_popup_click(service, 0)}>
                            {service}
                        </button>
                        {#if confirm_popup.value === service}
                            <div class="confirm-box footer" transition:fade={{ duration: 150 }}>
                                <div class="rwx-container">
                                    <!-- each block copy pasted from above -->
                                    {#each get_rwx_keys() as k}
                                        <div class="rwx-display">
                                            <div class="rwx-display-text">{rwx_display[k].value ? k : "-"}</div>
                                            <input
                                                type="checkbox"
                                                class="rwx-checkbox"
                                                bind:checked={rwx_display[k].value}
                                                on:change={() => validate_input()}
                                            />
                                        </div>
                                    {/each}
                                </div>
                                <div class="confirm-container">
                                    Add
                                    <label class="skip">
                                        <input
                                            type="checkbox"
                                            class="skip"
                                            bind:checked={confirm_popup.consent_given}
                                            disabled={rwx_values_off}
                                        />
                                    </label>
                                </div>
                                <button
                                    class="confirm-btn {ok_to_add ? 'ok' : ''}"
                                    disabled={!ok_to_add}
                                    on:click={async () => await request_update_service(Method.ADD)}
                                >
                                    Confirm
                                </button>
                            </div>
                        {/if}
                    </div>
                {/each}
            {/if}
        </div>
    </div>
{/if}

<style>
    :root {
        --service-button-border: #ee8b98 2px solid;
        --content-height: 40px;
    }
    p {
        margin-left: 10px;
    }
    span {
        margin: 0;
        padding: 0;
        border: none;
    }
    span.item-header {
        width: fit-content;
        border-bottom: 2px solid #c068689c;
    }
    .rwx-container {
        display: flex;
        flex-direction: row;
        justify-content: space-between;
        border-radius: 6px;
        padding: 8px;
        padding-top: 12px;
        margin-bottom: 10px;
        box-shadow: inset 0 0 5px #00000080; /* Inner shadow */

        border: 2px solid #c77070;
    }
    .rwx-checkbox {
        width: 18px;
        height: 18px;
        margin-top: 20px;
        margin-bottom: 8px;
    }

    .rwx-display {
        display: flex;
        flex-direction: column;
    }
    .rwx-display-text {
        margin-top: -10px;
        margin-bottom: -6px;
        font-size: 48px;
        font-family: "Lucida Console", monospace;
    }

    .item {
        display: flex;
        flex-direction: column;
        text-align: left;
    }
    .item.margin {
        margin: 2px;
    }
    .item-header {
        line-height: 14px;
        margin-top: 8px;
        color: #706370;
        font-size: 16px;
    }
    .item-footer {
        font-size: 22px;
    }
    .item-footer.rwx {
        font-size: 20px;
        color: #a85529;
        align-self: center;
    }

    label {
        display: inline-block;
        padding: 5px;
    }

    .top-content {
        font-size: 18px;
        margin-top: 4px;
        /* margin-bottom: 2px; */
        margin-left: 6px;
    }
    .confirm-container {
        display: flex;
        justify-content: space-between;
        white-space: nowrap;
        align-items: center;
        margin-left: 6px;
        margin-right: 4px;
        font-size: 16px;
    }

    .main {
        border: 3px solid #d364c3;
        border-radius: 6px;
        background-color: #fff0fc;
        display: flex;
        flex-direction: column;
        flex-wrap: wrap;
    }
    .header {
        margin: 4px;
        margin-bottom: 0px;
        font-size: 20px;
        padding: 0;
    }
    .content {
        display: flex;
        flex-direction: row;
        margin: 4px;
        display: flex;
        align-items: stretch;
        border-radius: 4px;
        border: 2px solid #804d7ab3;
        box-shadow: inset 0 0 4px #792a2a80;
    }
    .service-container {
        display: flex;
        height: 100%;
    }
    .update-access-btn,
    .add-access-btn {
        display: block;
        cursor: pointer;
        border: var(--service-button-border);
        background: #fff;
        margin: 5px;
        margin-right: 3px;
        font-size: 22px;
        font-weight: bolder;
        border-radius: 6px;
    }
    .add-access-btn {
        font-size: 24px;
        padding: 10px;
    }
    .update-access-btn:hover,
    .add-access-btn:hover {
        background: #b60bab1d;
        transition: 0.2s;
    }
    .confirm-box {
        display: flex;
        flex-direction: column;
        background: #fff;
        border: var(--service-button-border);
        position: absolute;
        border-radius: 6px;
        padding: 8px;
        width: 140px;
        transition: height 2s ease;
        box-shadow: 0 4px 8px #0000001a;
    }
    .confirm-box.upper {
        margin-top: 116px;
    }
    .confirm-box.footer {
        margin-top: 60px;
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
    .confirm-btn.del {
        background-color: #b92424;
        cursor: pointer;
        transition: 0.3s;
    }
</style>
