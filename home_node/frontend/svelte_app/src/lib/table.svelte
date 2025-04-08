<script lang="ts">
    import type { TableState } from "./table";

    import {
        is_arr,
        is_isodate,
        is_arr_empty,
        is_obj,
        is_obj_empty,
        is_str,
        strfloat_decimals,
        str_to_int,
    } from "$lib/utils/func";
    import { quintOut } from "svelte/easing";
    import { fly } from "svelte/transition";

    type S = $$Generic<T>;
    type P = $$Generic<R>;

    export let state: TableState<S, P>;

    const DATE_DECIMALS = 0;
    const FLOAT_DECIMALS = 3;
    let input_is_valid = true;
    const validate_input = (page_number: number | null) =>
        page_number !== null && state.page_num_ranges_validate(page_number) && !state.is_fetching_data
            ? page_number
            : null;
    const change_or_fetch_new_page = async (page_number: number | null) => {
        if (page_number !== null) {
            if (!state.pages.hasOwnProperty(page_number)) {
                try {
                    state.is_fetching_data = true; // Do not reset if throw, something went very wrong
                    await state.fetch_page(page_number);
                    state.is_fetching_data = false;
                } catch (e) {
                    input_is_valid = false;
                    throw e;
                }
            }
            state.page_number = page_number;
        }
        input_is_valid = true;
    };
    // #region Events
    const input_on_input = (event: Event) => {
        const tag = event.target as HTMLInputElement | null;
        if (tag) {
            const page_number = str_to_int(tag.value);
            if (page_number !== null) {
                input_is_valid = state.page_num_ranges_validate(page_number);
            } else {
                input_is_valid = false;
            }
        }
    };
    const input_on_key_down = (event: KeyboardEvent) => {
        if (event.key === "Enter") {
            input_on_blur(event);
            (event.target as HTMLInputElement | null)?.blur();
        }
    };
    const input_on_blur = async (event: Event) => {
        const tag = event.target as HTMLInputElement | null;
        if (tag) {
            await change_or_fetch_new_page(validate_input(str_to_int(tag.value)));
            tag.value = state.page_number.toString();
        }
    };
    const increase_page_btn = async (event: Event) => {
        const tag = event.target as HTMLButtonElement | null;
        if (tag) {
            const next_page = state.page_number + 1;
            if (state.page_num_ranges_validate(next_page)) {
                await change_or_fetch_new_page(next_page);
            }
            tag.value = state.page_number.toString();
        }
    };
    const decrease_page_btn = async (event: Event) => {
        const tag = event.target as HTMLButtonElement | null;
        if (tag) {
            const previous_page = state.page_number - 1;
            if (state.page_num_ranges_validate(previous_page)) {
                await change_or_fetch_new_page(previous_page);
            }
            tag.value = state.page_number.toString();
        }
    };
    // #endregion
</script>

{#if !is_obj_empty(state.pages)}
    <div class="main" in:fly={{ y: 250, easing: quintOut, delay: 100 }} out:fly={{ y: 250, easing: quintOut }}>
        <table>
            <thead>
                {#each state.columns as { display_name }}
                    <th>{display_name}</th>
                {/each}
            </thead>
            <tbody>
                {#each state.pages[state.page_number] as [row, callback_value]}
                    <tr on:click={() => state.on_row_click(callback_value)}>
                        {#each state.columns as { column_key }}
                            <td>
                                {#if !row.hasOwnProperty(column_key)}
                                    <div class="item-single">N/A</div>
                                {:else}
                                    {@const value = row[column_key]}
                                    {#if is_arr(value)}
                                        {#if is_arr_empty(value)}
                                            <div class="item-single">[]</div>
                                        {:else}
                                            <div class="item-container">
                                                {#if value.length === 2}
                                                    <div class="item-container-top">{value[0]}</div>
                                                    <div class="item-container-bot">{value[1]}</div>
                                                {:else}
                                                    {#each value.map( (v) => (is_str(v) ? v : v === null ? "None" : JSON.stringify(v)) ) as val}
                                                        <div class="item-container-multi">{val}</div>
                                                    {/each}
                                                {/if}
                                            </div>
                                        {/if}
                                    {:else if is_obj(value)}
                                        {#if is_obj_empty(value)}
                                            <div class="item-single">&#123;&#125;</div>
                                        {:else}
                                            {@const obj = Object.entries(value).map(
                                                (k, v) => `${k}: ${JSON.stringify(v)}`
                                            )}
                                            <div class="item-container">
                                                {#each obj as v}
                                                    <div class="item-container-multi obj">{v}</div>
                                                {/each}
                                            </div>
                                        {/if}
                                    {:else if value === null}
                                        <div class="item-single">None</div>
                                    {:else if is_str(value)}
                                        {#if is_isodate(value)}
                                            {@const [pfx, sfx] = value.split("T", 2)}
                                            {@const idx = sfx.lastIndexOf(".")}
                                            <div class="item-container">
                                                <div class="item-container-top date">{pfx}</div>
                                                <div class="item-container-bot date">
                                                    {idx === -1
                                                        ? sfx
                                                        : sfx.substring(0, idx) +
                                                          strfloat_decimals(
                                                              sfx.replace("Z", "").substring(idx),
                                                              DATE_DECIMALS
                                                          ) +
                                                          "Z"}
                                                </div>
                                            </div>
                                        {:else}
                                            <div class="item-single">{value}</div>
                                        {/if}
                                    {:else if typeof value === "number" && !Number.isInteger(value)}
                                        <div class="item-single">{strfloat_decimals(value, FLOAT_DECIMALS)}</div>
                                    {:else}
                                        <div class="item-single">{`${value}`}</div>
                                    {/if}
                                {/if}
                            </td>
                        {/each}
                    </tr>
                {/each}
            </tbody>
        </table>
        <tfoot>
            <div class="footer-count">
                {state.number_of_rows}
                {state.display_text}
            </div>
            <div class="page-swap">
                <button class="page-swap-btn left" disabled={state.page_number <= 1} on:click={decrease_page_btn}>
                    &#60;
                </button>
                <input
                    id="myinput"
                    class="page-swap-input"
                    class:err={!input_is_valid}
                    disabled={state.max_pages <= 1}
                    value={state.page_number}
                    on:input={input_on_input}
                    on:keydown={input_on_key_down}
                    on:blur={input_on_blur}
                />
                <div class="page-swap-print">/{state.max_pages}</div>
                <button
                    class="page-swap-btn right"
                    disabled={state.page_number >= state.max_pages}
                    on:click={increase_page_btn}>&#62;</button
                >
            </div>
        </tfoot>
    </div>
{/if}

<style>
    tfoot {
        display: flex;
        justify-content: space-between;
        width: 100%;
        padding-top: 8px;
        padding-bottom: 8px;
        background-color: #b0b0b0;
        align-items: center;
    }
    .page-swap-input {
        text-align: center;
        padding-top: 3px;
        width: 30px;
        font-weight: bolder;
        font-size: 16px;
        outline: none;
        height: 100%;
        box-sizing: border-box;
        border: none;
    }
    .page-swap-input:disabled {
        pointer-events: none;
    }
    .page-swap-input.err {
        box-shadow: inset 0 0 4px #ff1a1a;
    }
    .page-swap-btn {
        box-sizing: border-box;
        height: 100%;
        width: 32px;
        border: none;
        cursor: pointer;
        background-color: #cac9c9;
        transition: 0.2s;
    }
    .page-swap-btn:disabled {
        cursor: default;
    }
    .page-swap-btn:not:disabled:hover {
        background-color: #e0e0e0;
    }
    .page-swap-btn.left {
        border-radius: 14px 0 0 14px;
    }
    .page-swap-btn.right {
        border-radius: 0 14px 14px 0;
    }
    .page-swap {
        display: flex;
        padding-right: 10px;
        height: 36px;
        align-items: center;
    }
    .page-swap-print {
        pointer-events: none;
        margin-top: -2px;
        margin-left: 6px;
        margin-right: 4px;
        font-size: 18px;
    }
    .footer-count {
        padding-left: 10px;
        font-size: 18px;
    }
    .main {
        margin-top: 4px;
        border: rgb(174, 174, 174) 2px solid;
        box-sizing: border-box;
        border-radius: 14px;
        background-color: #cac9c9;
        overflow: hidden;
    }
    table {
        border-collapse: collapse;
        width: 100%;
    }
    th {
        padding: 6px;
        text-align: left;
        margin: auto;
        font-size: 22px;
        background-color: #b0b0b0;
    }
    tr {
        border-bottom: 2px #d7d7d7 solid;
        box-sizing: border-box;
        transition: 0.2s;
    }
    tr:last-child {
        border-bottom: none;
    }
    tr:hover {
        cursor: pointer;
        background: #bbbbbb;
    }

    .item-single {
        box-sizing: border-box;
        font-size: larger;
        padding-left: 12px;
    }
    .item-container {
        display: flex;
        margin: 6px;
        padding-left: 0px;
        background: none;
        box-sizing: border-box;
        flex-direction: column;
    }
    .item-container-top {
        font-size: 22px;
        padding-left: 0px;
    }
    .item-container-top.date {
        font-size: 20px;
    }
    .item-container-bot {
        font-size: 14px;
        padding-bottom: 8px;
    }
    .item-container-bot.date {
        font-size: 18px;
    }
    .item-container-multi {
        font-size: 14px;
    }
</style>
