<script lang="ts">
    import { enhance, applyAction } from "$app/forms";
    import { goto } from "$app/navigation";
    import { json, redirect } from "@sveltejs/kit";
    import type { ActionData } from "../../routes/login/$types";
    import { page } from "$app/stores";
    let form: ActionData;

    let show_pw: boolean = false;
    let btn_disabled: boolean = false;
</script>

<div class="card-main">
    <div class="card-child">
        <div class="card-header">Login</div>
        {#if form?.missing}<p class="error">Empty username or password</p>{/if}
        {#if form?.failed}<p class="error">Invalid username or password</p>{/if}
        <div class="card-body">
            <form
                method="POST"
                action="/login?/login"
                on:submit|preventDefault={() => (btn_disabled = true)}
                use:enhance={() => {
                    return async ({ result }) => {
                        await applyAction(result);
                        btn_disabled = false;
                        if ($page.url.pathname.toLowerCase().startsWith("/login")) {
                            return redirect(303, "/");
                        }
                        window.location.reload();
                    };
                }}
            >
                <div class="item">
                    <label
                        >Username
                        <input required type="text" name="form_user" value={form?.user ?? ""} />
                    </label>
                </div>
                <div class="item">
                    <label
                        >Password
                        <input required type={show_pw ? "text" : "password"} name="form_pwd" />
                    </label>
                    <button type="button" on:click={() => (show_pw = !show_pw)} class="show-pw">
                        {show_pw ? "Hide" : "Show"}
                    </button>
                </div>
                <div class="item remember">
                    <label class="remember-label">
                        <input type="checkbox" name="form_remember" value="1" />
                        Remember me
                    </label>
                </div>
                <div class="item button">
                    <button type="submit" class="form-submit" name="submit" disabled={btn_disabled}> Login </button>
                </div>
            </form>
        </div>
    </div>
</div>

<style>
    :root {
        --main-font-size: 1.5em;
        --child-font-size: 1.2em;
        --remember-size: 0.9em;
        --show-pw-size: 0.8em;
    }

    .error {
        font-weight: bold;
    }

    .card-main {
        background-color: #e3e3e3;
        border-radius: 10px;
        box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
        width: 400px;
        margin: auto;
        margin-top: 32px;
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
    }

    input {
        width: 100%;
        padding: 8px;
        box-sizing: border-box;
        border: none;
        outline: none;
        background-color: #f7f7f7;
        border-bottom: 2px solid #ccc;
        margin-top: 4px;
    }

    input:focus {
        width: 100%;
        padding: 8px;
        box-sizing: border-box;
        outline: none;
        background-color: #f7f7f7;
        border-bottom: 2px solid #45a049;
        margin-top: 4px;
        transition: border-bottom 0.4s, opacity 0.4s;
    }

    /* Show password inside input password */
    .show-pw {
        font-weight: bold;
        font-size: var(--remember-size);
        float: right;
        margin-left: -25px;
        margin-right: 5px;
        margin-top: -26px;
        position: relative;
        background: none;
        border: none;
        z-index: 2;
    }

    /* Remember me */
    input[type="checkbox"] {
        width: 16px;
        margin-top: 2px;
        float: left;
    }

    .remember {
        display: flex;
        float: right;
        width: 100%;
        font-size: var(--show-pw-size);
    }

    .remember-label {
        margin-top: 3px;
        margin-left: 2px;
    }

    /* Login button */
    .form-submit {
        background-color: #228625;
        color: #fff;
        padding: 10px;
        border: None;
        width: 20%;
        border-radius: 4px;
        cursor: pointer;
        transition: background-color 0.2s, opacity 0.2s;
    }

    .form-submit:hover {
        background-color: #45a049;
    }

    .form-submit:disabled {
        background-color: #a9a9a9; /* Gray */
        color: #808080; /* Dark gray for text */
        cursor: not-allowed;
    }

    /* Less important */
    .item {
        margin-bottom: 15px;
    }
</style>
