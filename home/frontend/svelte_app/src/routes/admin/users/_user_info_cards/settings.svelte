<script lang="ts">
    import type { User } from "$lib/utils/const";
    import { HTTP_METHOD as HTTP_METHOD } from "$lib/utils/const";
    import { fade } from "svelte/transition";
    import {
        check_creds_then_fetch as check_creds_fetch,
        validate_mail,
        validate_name_length,
        validate_password,
    } from "$lib/utils/func";
    import { InfoPopup, StateCSS, TextInput } from "$lib/utils/ui-state";

    export let user: User;

    let confirmation_popup = new InfoPopup<boolean>();
    const input_states = {
        mail: new TextInput(user.login.mail, validate_mail, "mail"),
        name: new TextInput(user.login.name, validate_name_length, "name"),
        data_name: new TextInput(user.data.name, validate_name_length, "data_name"),
        password: new TextInput("", validate_password, "password"),
    };

    type InputStateKey = keyof typeof input_states;
    let valid_input = false;
    let init_state = true;

    const reset_state = () => {
        confirmation_popup = confirmation_popup.set_value(null);
        (Object.keys(input_states) as InputStateKey[]).forEach((k) => (input_states[k] = input_states[k].reset()));
        valid_input = false;
        init_state = true;
    };

    const apply_btn_event = () => (confirmation_popup = confirmation_popup.set_value(true));
    const input_event = (k: InputStateKey, b: boolean) => {
        input_states[k] = input_states[k].update_state(b);
        update_init_state();
        update_valid_input();
    };

    const request_update = async () => {
        if (!confirmation_popup.consent_given) {
            alert("Consent not given");
            return;
        }
        confirmation_popup = confirmation_popup.off();
        const defer = () => {
            valid_input = false; // golang-inspired defer
            confirmation_popup = confirmation_popup.on();
        };
        update_init_state();
        update_valid_input();
        if (init_state || !valid_input) {
            alert("Input should be valid..");
        } else {
            const new_settings = get_payload();
            let update_list: InputStateKey[] = Object.keys(new_settings) as InputStateKey[];
            let resp = await check_creds_fetch(HTTP_METHOD.PATCH, `user/${user.user_id}`, JSON.stringify(new_settings));
            if (!resp.ok) {
                const data = await resp.json();
                const { fail, success }: { fail: InputStateKey[]; success: InputStateKey[] } = JSON.parse(data.detail);
                update_list = success;
                fail.forEach((k) => (input_states[k] = input_states[k].set_state(StateCSS.INVALID)));
                alert(JSON.stringify(data));
            }
            if (update_list.length !== 0) {
                update_list.forEach((k) => {
                    let new_value = new_settings[k];
                    switch (k) {
                        case "name":
                            user.login.name = new_value;
                            break;
                        case "mail":
                            user.login.mail = new_value;
                            break;
                        case "data_name":
                            user.data.name = new_value;
                            break;
                        case "password":
                            new_value = "";
                    }
                    input_states[k] = input_states[k].reset(new_value);
                });
                update_init_state();
                user = user;
            }
        }
        defer();
    };

    const close_confirm_box = (event: MouseEvent) => {
        if (confirmation_popup.value) {
            const tag = event.target as HTMLElement | null;
            const ignore =
                (tag instanceof HTMLButtonElement && tag.classList.contains("apply-btn")) || btn_group.contains(tag);
            if (!ignore) {
                confirmation_popup = confirmation_popup.set_value(null);
            }
        }
    };
    const update_valid_input = () => {
        for (const input of Object.values(input_states)) {
            if (!input.is_valid()) {
                valid_input = false;
                return;
            }
        }
        valid_input = true;
    };
    const update_init_state = () => {
        for (const input of Object.values(input_states)) {
            if (input.get_state() !== StateCSS.DEFAULT) {
                init_state = false;
                return;
            }
        }
        init_state = true;
    };
    const get_payload = (): { [key: string]: string } =>
        Object.fromEntries(
            Object.entries(input_states)
                .map(([k, v]) => [k, v.get_value()])
                .filter(([_, v]) => v !== null)
        );
    let btn_group: HTMLDivElement;
    $: ok_to_send =
        confirmation_popup.consent_given &&
        valid_input &&
        !init_state &&
        confirmation_popup.value &&
        confirmation_popup.enabled;
</script>

<svelte:window on:click={close_confirm_box} />
<div class="main">
    <div class="header">
        <p>Settings</p>
    </div>
    <div class="container">
        <div class="item-container">
            <div class="item">
                <div class="item-key">Login</div>
                <input
                    id="login"
                    bind:value={input_states.name.value}
                    class={input_states.name.state}
                    on:input={() => input_event("name", true)}
                />
            </div>
        </div>
        <div class="item-container">
            <div class="item">
                <div class="item-key">Mail</div>
                <input
                    id="mail"
                    type="email"
                    class={input_states.mail.state}
                    bind:value={input_states.mail.value}
                    on:input={() => input_event("mail", true)}
                />
            </div>
        </div>
        <div class="item-container">
            <div class="item">
                <div class="item-key">Password</div>
                <input
                    id="password"
                    type="password"
                    class={input_states.password.state}
                    bind:value={input_states.password.value}
                    on:input={() => input_event("password", false)}
                />
            </div>
        </div>
        <div class="item-container">
            <div class="item">
                <div class="item-key">Username (App)</div>
                <input
                    id="display_name"
                    class={input_states.data_name.state}
                    bind:value={input_states.data_name.value}
                    on:input={() => input_event("data_name", false)}
                />
            </div>
        </div>
    </div>
    <div class="btn-group" bind:this={btn_group}>
        <button class="reset-btn {init_state ? '' : 'ok'} skip" on:click={reset_state} disabled={init_state}
            >Reset</button
        >
        <div class="btn-container">
            <button class="apply-btn {valid_input ? 'ok' : ''} skip" on:click={apply_btn_event} disabled={!valid_input}
                >Apply updates</button
            >
            {#if confirmation_popup.value}
                <div id="confirm-box" class="skip" transition:fade={{ duration: 150 }}>
                    <div class="confirm-container skip">
                        Update
                        <label class="skip">
                            <input type="checkbox" class="skip" bind:checked={confirmation_popup.consent_given} />
                        </label>
                    </div>
                    <button
                        class="confirm-btn skip {ok_to_send ? 'ok' : ''}"
                        disabled={!ok_to_send}
                        on:click={request_update}
                    >
                        Confirm
                    </button>
                </div>
            {/if}
        </div>
    </div>
</div>

<style>
    .btn-group {
        display: flex;
        flex-direction: row;
    }
    .ok {
        background-color: #bdf3ba;
    }
    .error {
        background-color: #ffadad;
    }
    :root {
        --button-border: #46a8b744 2px solid;
        --content-height: 52px;
    }
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
    input {
        font-size: 20px;
        border: 2px #bfbfbf solid;
        border-radius: 6px;
        padding-left: 6px;
    }
    .btn-container {
        display: flex;
        height: 100%;
    }
    .confirm-container {
        display: flex;
        white-space: nowrap;
        align-items: center;
        font-size: 16px;
    }
    .container {
        display: flex;
        flex-wrap: wrap;
        margin: 4px;
        padding: 4px;
        border-radius: 4px;
        border: 2px solid rgba(50, 169, 167, 0.869);
        box-shadow: inset 0 0 4px rgba(121, 42, 42, 0.5);
    }
    .item-container {
        flex: 0 0 50%;
        margin: 0;
        padding: 0;
        display: flex;
    }
    .item {
        display: flex;
        flex-direction: column;
        padding: 6px;
        margin: 2px;
        width: 100%;
        border-radius: 8px;
        box-sizing: border-box;
        border: rgb(181, 215, 214) 2px solid;
    }
    .item-key {
        font-size: 18px;
        padding: 2px;
        padding-top: 0;
    }

    .main {
        border: 3px solid rgb(25, 186, 168);
        border-radius: 6px;
        background-color: #e6f1f1;
        display: flex;
        flex-direction: column;
        flex-wrap: wrap;
    }
    .header {
        display: flex;
        flex-direction: row;
    }

    .apply-btn {
        white-space: nowrap;
        /* cursor: pointer; */
        border: var(--button-border);
        background: none;
        margin: 8px;
        margin-top: 4px;
        font-size: 22px;
        font-weight: bolder;
        background: #489ca997;
        border-radius: 6px;
        transition: 0.3s;
        box-shadow: 0 0 4px 2px rgba(0, 0, 0, 0.337);
    }
    .apply-btn.ok {
        background: #57bece97;
        cursor: pointer;
        transition: 0.3s;
    }
    .apply-btn.ok:hover {
        background: rgba(94, 113, 222, 0.53);
        transition: 0.2s;
    }
    .reset-btn {
        white-space: nowrap;
        /* cursor: pointer; */
        border: var(--button-border);
        background: none;
        margin: 8px;
        margin-top: 4px;
        font-size: 22px;
        font-weight: bolder;
        background: #dc505097;
        border-radius: 6px;
        transition: 0.3s;
        box-shadow: 0 0 4px 2px rgba(0, 0, 0, 0.337);
    }
    .reset-btn.ok {
        background: #ff3434;
        cursor: pointer;
        transition: 0.3s;
    }
    .reset-btn.ok:hover {
        background: #a35a5a;
        transition: 0.2s;
    }
    #confirm-box {
        display: flex;
        flex-direction: column;
        background: #fff;
        border: var(--button-border);
        position: absolute;
        border-radius: 6px;
        padding: 8px;
        margin-left: 8px;
        margin-top: var(--content-height);
        width: 92px;
        transition: height 2s ease;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
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
