<script lang="ts" context="module">
    export let input_element: HTMLInputElement;
</script>

<script lang="ts">
    export let placeholder: string | undefined = undefined;
    export let on_input_callback: (value: string) => void = () => {};
    export let on_focus_callback: () => void = () => {};
    export let on_clear_callback: () => void = () => {};
    export let on_input_enter: () => void = () => {};

    let clear_button_hidden = true;

    const on_enter_key = (event: KeyboardEvent) => {
        const tag = event.target as HTMLInputElement;
        if (tag?.value && event.key === "Enter") {
            on_input_callback(tag.value);
            on_input_enter();
        }
    };
    const on_input = (event: Event) => {
        const tag = event.target as HTMLButtonElement;
        if (tag) {
            on_input_callback(tag.value);
            clear_button_hidden = tag.value === "";
        }
    };
    const on_clear_click = (_: Event) => {
        input_element.value = "";
        clear_button_hidden = true;
        on_clear_callback();
    };
</script>

<div class="main">
    <div class="input-container">
        <input
            id="input"
            type="text"
            bind:this={input_element}
            on:keydown={on_enter_key}
            on:focus={on_focus_callback}
            on:blur={on_input}
            on:input={on_input}
            {placeholder}
        />
        <button id="clear-btn" class:hidden={clear_button_hidden} on:click={on_clear_click}> X </button>
    </div>
</div>

<style>
    ::placeholder,
    input {
        color: #28464ae3;
    }
    .main {
        margin: 0;
        padding: 0;
        display: flex;
    }
    .input-container {
        position: relative;
        width: var(--width);
    }
    .hidden {
        visibility: hidden;
    }
    #clear-btn {
        position: absolute;
        right: 10px;
        top: 46%;
        transform: translateY(-50%) scaleY(0.8);
        border: none;
        background: transparent;
        cursor: pointer;
        font-size: 26px;
        color: #28464ae3;
        padding: 0;
        outline: none;
    }

    #clear-btn:hover {
        color: #4cb3c3;
    }

    #input {
        font-size: 18px;
        width: 100%;
        margin: auto;
        border-radius: 10px;
        padding-top: 8px;
        padding-left: 6px;
        padding-bottom: 5px;
        box-sizing: border-box;
        border: none;
        outline: none;
        border-bottom: 3px solid transparent;
        background-color: #f7f7f7;
        transition: 0.4s;
    }

    #input:focus {
        box-sizing: border-box;
        border-bottom-color: #4cb3c3;
        background-color: #f7f7f7;
    }
</style>
