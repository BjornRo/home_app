<script lang="ts" context="module">
    export let element_history_popup: HTMLDivElement;
    export type SearchText = string;
</script>

<script lang="ts">
    import type { User } from "$lib/utils/const";
    import { fly } from "svelte/transition";
    import type { Pages, Row } from "$lib/table";

    export let history: { [key: SearchText]: Row<string, User>[] };
    export let valid: boolean;
    export let on_click_callback: () => void = () => {};
    export let on_item_click_callback: (history: Row<string, User>[]) => void = () => {};

    // let count = 0;
    // Object.values(history).forEach((element) => {
    //     count += element.length;
    // });
    // return count;
    const count_rows = (history: Row<string, User>[]) =>
        Object.values(history).reduce((count, element) => count + element.length, 0);

    $: history_items = Object.entries(history);
</script>

<div class="main" class:ok={valid} in:fly={{ x: -75 }} out:fly={{ x: -75 }} bind:this={element_history_popup}>
    <div class="container" class:ok={valid}>
        <div class="header">
            <p>Previous searches</p>
            <button class="close" on:click={on_click_callback}>x</button>
        </div>
        <div class="body">
            {#if history_items.length === 0}
                <span class="items-empty">Empty</span>
            {:else}
                {#each history_items as [search_text, numrows]}
                    <button
                        class="item-btn"
                        on:click={() => on_item_click_callback(numrows)}
                        disabled={Object.keys(numrows).length === 0}
                    >
                        <span class="result-container">
                            {#each [["Search query", search_text], ["Count", count_rows(numrows)]] as [k, v]}
                                <span class="item-result">
                                    <span class="item-result top">{k}</span>
                                    <span class="item-result bot">{v}</span>
                                </span>
                            {/each}
                        </span>
                    </button>
                {/each}
            {/if}
        </div>
    </div>
</div>

<style>
    :global(.main) {
        --bg-color: #f5f5f5;
    }
    .main {
        position: relative;
        width: var(--width);
        top: 8px;
    }
    /* Popup arrow */
    .main::after {
        content: "";
        position: absolute;
        bottom: 100%;
        left: 50%;

        margin-left: -10px;
        border-width: 10px;
        border-style: solid;
        transition: 0.4s;
        border-color: transparent transparent var(--invalid) transparent;
    }
    .main.ok::after {
        transition: 0.4s;
        border-color: transparent transparent var(--valid) transparent;
    }
    .container {
        display: flex;
        margin: auto;
        width: 80%;
        flex-direction: column;
        background-color: var(--bg-color);
        border: solid 6px var(--invalid);
        box-shadow: 0 0 10px 5px #4c4848;
        padding: 4px;
        border-radius: 10px;
        transition: 0.4s;
    }
    .container.ok {
        transition: 0.4s;
        border-color: var(--valid);
    }
    .header {
        display: flex;
        flex-direction: row;
        justify-content: space-between;
        align-items: center;
        font-size: 15px;
    }
    p {
        margin: 4px;
        margin-bottom: 0px;
    }
    .body {
        height: 100%;
        text-align: center;
        border-radius: 6px;
        display: flex;
        flex-direction: column;
        padding: 4px;
        box-shadow: inset 0 0 4px 2px #706060;
    }
    .items-empty {
        padding: 6px;
        margin: auto;
        margin-top: 6px;
        margin-bottom: 6px;
        border-radius: 6px;
        color: #839597e3;
        border: #dbbfdc 3px solid;
    }
    .item-btn {
        font-size: 16px;
        margin: 4px;
        background: none;
        border: 2px solid #9f9fbc;
        border-radius: 6px;
        cursor: pointer;
        transition: 0.4s;
    }
    .item-btn:hover:enabled {
        background: #e1e0e0;
    }
    .item-btn:disabled {
        border: 2px solid #9595a9;
        cursor: default;
    }
    .result-container {
        flex-direction: row;
        justify-content: space-between;
        gap: 24px;
    }
    .item-result {
        display: flex;
        margin: 0;
        padding: 0;
    }
    .item-result.top {
        font-size: 15px;
        text-decoration: underline;
        text-decoration-thickness: 2px;
        text-decoration-color: #d19d9d;
    }
    .item-result.bot {
        font-size: 17px;
    }

    button.close {
        border: 2px solid #978b8b;
        margin: 6px;
        cursor: pointer;
        padding-bottom: 2px;
        border-radius: 6px;
        background: none;
        transition: 0.3s;
    }
    button.close:hover {
        background: #e4e4e4;
    }
</style>
