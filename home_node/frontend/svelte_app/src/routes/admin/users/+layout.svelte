<script lang="ts">
    import { page } from "$app/stores";

    import Modal from "$lib/modal.svelte";
    import { toast, ToastType } from "$lib/toast_notification.svelte";
    import type { LiteStarException } from "$lib/utils/const";
    import { check_creds_then_post, validate_mail, validate_password } from "$lib/utils/func";

    let st = {
        visible: false,
        show_pw: false,
        reset_btn_disabled: true,
        valid_input: false,
        text: { username: "", mail: "None", password: "" },
        valid: { username: false, mail: true, password: false },
        invalid: {
            username: [] as string[],
            mail: [] as string[],
        },
    };
    type MyState = typeof st;
    const DEFAULT_STATE = JSON.stringify(st);
    const DEFAULT_INPUTS = JSON.stringify(st.text);
    export const default_state = (): MyState => JSON.parse(DEFAULT_STATE);
    $: route_id = $page.route.id!;

    const reset = () => {
        st = default_state();
        st.visible = true;
    };
    const submit = async () => {
        if (!st.valid_input) {
            return;
        }
        st.valid_input = false;
        const ST = st.text;
        const PAYLOAD = {
            name: ST.username,
            pwd: ST.password,
            mail: ST.mail.toLowerCase() === "none" ? null : ST.mail,
        };
        const resp = await check_creds_then_post("register", PAYLOAD);
        const NEW_MAIL = ST.mail.toLowerCase();
        const NEW_USER = ST.username.toLowerCase();
        if (resp.ok) {
            st.invalid.username.push(NEW_USER);
            toast.emit(`${ST.username} successfully added!`, ToastType.SUCCESS);
            st.valid.username = false;
            if (NEW_MAIL !== "none") {
                toast.emit(`${ST.mail} successfully added!`, ToastType.SUCCESS);
                st.invalid.mail.push(NEW_MAIL);
                st.valid.mail = false;
            }
        } else {
            const msg = (await resp.json()) as LiteStarException;
            const detail = msg.detail.toLowerCase();
            toast.emit(`Status code: ${msg.status_code} | Detail: ${msg.detail}`, ToastType.ERROR);
            if (detail.includes("mail")) {
                st.invalid.mail.push(NEW_MAIL);
                st.valid.mail = false;
            } else if (detail.includes("user")) {
                st.invalid.username.push(NEW_USER);
                st.valid.username = false;
            } else {
                st.valid.mail = NEW_MAIL === "none";
                st.valid.username = false;
                alert(`Unknown error: ${msg.status_code}, ${detail}`);
            }
        }
    };
    const on_input = () => {
        const f = st.text;
        st.valid.username = 1 <= f.username.length && !st.invalid.username.includes(f.username.toLowerCase());
        st.valid.password = validate_password(f.password);
        st.valid.mail =
            (f.mail.toLowerCase() === "none" || validate_mail(f.mail)) &&
            !st.invalid.mail.includes(f.mail.toLowerCase());
        st.reset_btn_disabled = JSON.stringify(st.text) === DEFAULT_INPUTS;
        st.valid_input = Object.values(st.valid).every((v) => v);
    };
    const on_key_press = async (event: KeyboardEvent) => {
        if (event.key === "Enter") {
            await submit();
        }
    };
</script>

<Modal bind:visible={st.visible}>
    <div class="card-main">
        <div class="card-child">
            <div class="card-header">Add user</div>
            <div class="card-body">
                <div class="item">
                    <label
                        >Username
                        <input
                            class:error={!st.valid.username}
                            type="text"
                            name="field0"
                            bind:value={st.text.username}
                            on:keypress={on_key_press}
                            on:blur={on_input}
                            on:input={on_input}
                        />
                    </label>
                </div>
                <div class="item">
                    <label
                        >Mail
                        <input
                            class:error={!st.valid.mail}
                            type="text"
                            name="field1"
                            bind:value={st.text.mail}
                            on:keypress={on_key_press}
                            on:blur={on_input}
                            on:input={on_input}
                        />
                    </label>
                </div>
                <div class="item">
                    <label
                        >Password
                        {#if st.show_pw}
                            <input
                                class:error={!st.valid.password}
                                type="text"
                                name="field2"
                                bind:value={st.text.password}
                                on:keypress={on_key_press}
                                on:blur={on_input}
                                on:input={on_input}
                            />
                        {:else}
                            <input
                                class:error={!st.valid.password}
                                type="password"
                                name="field3"
                                bind:value={st.text.password}
                                on:blur={on_input}
                                on:input={on_input}
                            />
                        {/if}
                    </label>
                    <button type="button" class="show-pw" on:click={() => (st.show_pw = !st.show_pw)}>
                        {st.show_pw ? "Hide" : "Show"}
                    </button>
                </div>
                <div class="item button">
                    <button class="btn submit" on:click={submit} disabled={!st.valid_input}>Submit</button>
                    <button class="btn reset" on:click={reset} disabled={st.reset_btn_disabled}>Reset </button>
                </div>
            </div>
        </div>
    </div>
</Modal>

<div class="main">
    <div class="titlebar">
        <div class="titlebar-title">App users</div>
        <button class="add-user-btn" on:click={() => (st.visible = true)}>+ Add user</button>
    </div>
    <div class="navbar">
        <a href="/admin/users" class:active={route_id.endsWith("users")} class="navbar-item">All users</a>
        <a href="/admin/users/search" class:active={route_id.endsWith("search")} class="navbar-item">Search</a>
    </div>
    <div class="content">
        <slot />
    </div>
</div>

<style>
    .navbar-item {
        font-family: "Helvetica", sans-serif;
        display: flex;
        padding-top: 4px;
        align-items: center;
        justify-content: center;
        color: #cfcfcf;
        text-decoration: none;
        background: none;
        font-size: 20px;
        border-bottom: 4px solid #ffffff00 !important;
        border-radius: 0px;
        width: 120px;
        height: 40px;
        transition: 0.5s;
        box-sizing: border-box;
    }
    .navbar-item.active {
        color: rgb(225, 225, 225) !important;
        border-bottom: 4px solid rgb(48, 179, 191) !important;
    }
    .navbar-item:hover {
        background: #c6b8b841 !important;
        border-radius: 6px;
    }
    .navbar {
        padding-left: 16px;
        display: flex;
        height: 40px;
        background: #a1bec62f;
        gap: 12px;
        align-items: center;
        padding-bottom: 2px;
    }
    .card-main {
        background-color: #e3e3e3;
        border-radius: 10px;
        box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
        width: 600px;
        margin: auto;
        font-family: "Helvetica", sans-serif;
    }

    .card-child {
        padding: 20px;
        padding-bottom: 5px;
    }

    .card-header {
        font-size: var(--main-font-size);
        font-weight: bold;
        margin-bottom: 20px;
    }

    label {
        font-size: var(--child-font-size);
        color: #333;
        font-size: 20px;
    }

    input {
        width: 100%;
        padding: 8px;
        font-size: 22px;
        box-sizing: border-box;
        border: none;
        border-bottom: 2px solid #29a93c;
        outline: none;
        background-color: #f7f7f7;
        margin-top: 4px;
        transition: 0.4s;
    }

    input.error {
        width: 100%;
        padding: 8px;
        box-sizing: border-box;
        outline: none;
        background-color: #f7f7f7;
        border-bottom: 2px solid #c22020;
        margin-top: 4px;
    }

    .item.button {
        display: flex;
        gap: 16px;
    }
    /* Show password inside input password */
    .show-pw {
        font-weight: bold;
        font-size: var(--remember-size);
        float: right;
        margin-left: -25px;
        margin-right: 4px;
        margin-top: -31px;
        font-size: 17px;
        position: relative;
        background: none;
        border: none;
        outline: none;
        transition: 0.6s;
        z-index: 2;
    }

    .btn {
        color: #ffffffc2;
        padding: 10px;
        border: None;
        font-size: 22px;
        border-radius: 4px;
        cursor: pointer;
        transition: 0.2s;
    }
    .btn.reset {
        background-color: #d16818;
    }
    .btn.submit {
        background-color: #258270;
    }

    .btn:hover {
        background-color: #568e59af;
    }

    .btn:disabled {
        background-color: #a9a9a9; /* Gray */
        color: #808080; /* Dark gray for text */
        cursor: not-allowed;
    }
    /* Less important */
    .item {
        margin-bottom: 18px;
    }
    .content {
        display: flex;
        align-items: stretch;
        height: 100%;
        width: 100%;
        /* Allow content to take up remaining space */
        flex-grow: 1;
        /* Enable vertical scrolling */
        overflow-y: auto;
    }
    .main {
        display: flex;
        align-items: stretch;
        flex-direction: column;
        width: 100%;
        height: 100%;
    }
    .titlebar {
        display: flex;
        height: 50px;
        width: 100%;
        justify-content: flex-start;
        align-items: center;
        background-color: #399a91;
        color: white;
        /* flex-direction: row; */
        gap: 10px;
    }
    .titlebar-title {
        margin: auto;
        margin-left: 12px;
        font-size: 26px;
    }
    .add-user-btn {
        width: 128px;
        outline: none;
        background: #53acc8;
        border: 2px solid #3859419f;
        border-radius: 8px;
        color: #080d119f;
        margin-right: 8px;
        font-size: 20px;
        cursor: pointer;
        transition: 0.3s;
        height: 80%;
    }
    .add-user-btn:hover {
        background: #5ba9c6;
    }
</style>
