<script lang="ts" context="module">
    export type NumberRows = { [keys: string]: Rows };
    export interface Header {
        display_name: string;
        column_key: string;
    }
    export interface RowData {
        [key: string]: any;
    }
    export interface InputData {
        headers: Header[];
        current_page_number: number;
        rows_per_page: number;
        all_rows: NumberRows;
        display_count: { text: string; count: number };
    }
    export type UserRow = [User, RowData];
    export type Rows = Array<[RowData, () => void]>;

    export const dfetch_more_rows = (offset: number): null => {
        return null;
    };
</script>

<script lang="ts">
    import type { User, UserID } from "$lib/utils/const";

    import { is_arr, is_arr_empty, is_isodate, is_int, is_obj, is_obj_empty, is_str } from "$lib/utils/func";
    import { quintOut } from "svelte/easing";
    import { fly } from "svelte/transition";

    // Order given and filters rows. If row-key is undefined -> N/A. null -> None
    export let data: InputData;

    // Store to check if user entered a valid value. page.current.. is bound to input.
    let current_page_rows = get_page_rows(data.current_page_number);
    const MAX_PAGES = Math.ceil(data.display_count.count / data.rows_per_page);
    const DATE_DECIMALS = 0;
    const FLOAT_DECIMALS = 3;

    const reshape_row = (row: RowData) => {
        let items: Array<{ cls: string; val: string } | Array<{ cls: string; val: string | [string, string] }>> = [];
        for (const { column_key } of data.headers) {
            if (!row.hasOwnProperty(column_key)) {
                items.push({ cls: "", val: "N/A" });
                continue;
            }

            const value: any = row[column_key];
            if (is_arr(value)) {
                if (is_arr_empty(value)) {
                    items.push({ cls: "", val: "[]" });
                } else {
                    items.push(
                        value.map((v) => ({ cls: "", val: is_str(v) ? v : v === null ? "None" : JSON.stringify(v) }))
                    );
                }
            } else if (is_obj(value)) {
                if (is_obj_empty(value)) {
                    items.push({ cls: "", val: "{}" });
                } else {
                    items.push(
                        Object.entries(value).map(([key, value]) => ({
                            cls: "obj",
                            val: [key, JSON.stringify([key, value])],
                        }))
                    );
                }
            } else if (value === null) {
                items.push({ cls: "", val: "None" });
            } else if (is_str(value)) {
                if (is_isodate(value)) {
                    // isotime, no numbers
                    const date = value.split("T");
                    const end = date[1].lastIndexOf(".");
                    if (end) {
                        date[1] = date[1].substring(0, DATE_DECIMALS ? end + DATE_DECIMALS + 1 : end);
                    }
                    items.push(date.map((v) => ({ cls: "date", val: v })));
                } else {
                    items.push({ cls: "", val: value });
                }
            } else {
                let new_value = `${value}`;
                if (new_value.includes(".")) {
                    let [a, b] = new_value.split(".", 1);
                    new_value = a + (b === undefined ? "" : "." + b.substring(0, FLOAT_DECIMALS));
                }
                items.push({ cls: "", val: new_value });
            }
        }
        return items;
    };

    const input_on_input = (event: Event) => {
        const tag = event.target as HTMLInputElement | null;
        if (tag) {
            const value = tag.value.trim();
            if (is_int(value)) {
                const num = parseInt(value);
                if (0 < num && num <= MAX_PAGES) {
                    tag.classList.remove("err");
                    return;
                }
            }
            tag.classList.add("err");
        }
    };
    const input_on_blur = (event: Event) => {
        const tag = event.target as HTMLInputElement | null;
        if (tag) {
            let num = -1;
            const value = tag.value.trim();
            if (is_int(value)) {
                num = parseInt(value);
                if (!(0 < num && num <= MAX_PAGES)) {
                    num = -1;
                }
            }
            if (num !== -1) {
                data.current_page_number = num;
                data.current_page_rows = get_page_rows(num);
            }
            tag.value = current_page_num.toString();
            tag.classList.remove("err");
        }
    };
    const input_on_focus = (event: Event) => {
        if (MAX_PAGES === 1) {
            (event.target as HTMLInputElement | null)?.blur();
        }
    };
    const input_on_key_down = (event: KeyboardEvent) => {
        if (event.key === "Enter") {
            input_on_blur(event);
            (event.target as HTMLInputElement | null)?.blur();
        }
    };

    const change_page_btn = (event: Event) => {
        const tag = event.target as HTMLButtonElement | null;
        if (tag) {
            const increment = tag.classList.contains("right");
            let val = 0;
            if (increment) {
                if (data.current_page_number < MAX_PAGES) {
                    val = 1;
                }
            } else if (1 < data.current_page_number) {
                val = -1;
            }
            if (val !== 0) {
                current_page_num += val;
                data.current_page_number += val;
                current_page_rows = get_page_rows(current_page_num);
            }
        }
    };
    function get_page_rows(page_num: number) {
        const val = data.rows_per_page * page_num;
        return data.all_rows.slice(val - data.rows_per_page, val + 1);
    }
</script>

{#if !is_arr_empty(data.headers) && !is_arr_empty(data.all_rows)}
    <div class="main" in:fly={{ y: 250, easing: quintOut, delay: 100 }} out:fly={{ y: 250, easing: quintOut }}>
        <table>
            <thead>
                {#each data.headers as header}
                    <th>{header.display_name}</th>
                {/each}
            </thead>
            <tbody>
                {#each current_page_rows as [row, callback]}
                    <tr on:click={callback}>
                        {#each reshape_row(row) as item_parts}
                            <td>
                                {#if !is_arr(item_parts)}
                                    <div class="item-single">{item_parts.val}</div>
                                {:else}
                                    <div class="item-container">
                                        {#if item_parts.length === 2}
                                            {#each ["top", "bot"] as ctype, i}
                                                <div class="item-container-{ctype} {item_parts[i].cls}">
                                                    {item_parts[i].val}
                                                </div>
                                            {/each}
                                        {:else}
                                            {#each item_parts as sub_part}
                                                <div class="item-container-multi {sub_part.cls}">
                                                    {sub_part.val}
                                                </div>
                                            {/each}
                                        {/if}
                                    </div>
                                {/if}
                            </td>
                        {/each}
                    </tr>
                {/each}
            </tbody>
        </table>
        <tfoot>
            <div class="footer-count">
                {display_count.count}
                {display_count.text}
            </div>
            <div class="page-swap">
                <button class="page-swap-btn left" disabled={current_page_num === 1} on:click={change_page_btn}
                    >{"<"}</button
                >
                <input
                    id="myinput"
                    class="page-swap-input"
                    bind:value={data.current_page_number}
                    on:input={input_on_input}
                    on:blur={input_on_blur}
                    on:focus={input_on_focus}
                    on:keydown={input_on_key_down}
                    disabled={MAX_PAGES === 1}
                />
                <div class="page-swap-print">/{MAX_PAGES}</div>
                <button class="page-swap-btn right" disabled={current_page_num === MAX_PAGES} on:click={change_page_btn}
                    >{">"}</button
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
        /* border: 2px solid blue; */
        padding-right: 10px;
        height: 36px;
        align-items: center;
    }
    .page-swap-print {
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
