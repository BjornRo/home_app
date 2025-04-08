<script lang="ts" async>
    import { type User } from "$lib/utils/const";
    import { is_mobile_view } from "$lib/utils/stores";
    import {
        validate_mail,
        validate_name_length,
        validate_guid,
        check_creds_then_fetch,
        is_obj_empty,
        contains,
    } from "$lib/utils/func";
    import { get } from "svelte/store";
    import UserInfoModal from "../user_info_modal.svelte";
    import { type Pages, type Row, TableState } from "$lib/table";
    import Table from "$lib/table.svelte";
    import MagnifyingGlass from "$lib/icons/magnifying_glass.svelte";
    import SearchInput, { input_element } from "./search_input.svelte";
    import { input_element as search_input_element } from "./search_input.svelte";
    import HistoryPopup from "./history_popup.svelte";
    import { element_history_popup, type SearchText } from "./history_popup.svelte";
    import { convert_user_list_to_rows, HEADERS, MOBILE_FILTER_HEADERS, type HeaderKeys } from "$lib/admin/user_utils";
    import { toast } from "$lib/toast_notification.svelte";

    export let data;

    const SEARCH_BAR_WIDTH = 320;

    const STATE = {
        table: new TableState<HeaderKeys, User>(
            data.rows_per_page,
            HEADERS,
            "found",
            0,
            (user) => (STATE.selected_user = user)
        ),
        has_searched: false,
        exact_match: false,
        selected_user: null as User | null,
        not_found_str: "",

        invalid_inputs: [""] as string[],
        valid_inputs: {} as { mail?: string; name?: string; user_id?: string }, // Add/remove values if (in)valid

        history_popup_visible: false,
        history: {} as { [key: SearchText]: Row<HeaderKeys, User>[] },
        all_fetched: {
            user_id: {} as { [key: string]: User },
            name: {} as { [key: string]: User },
            mail: {} as { [key: string]: User },
        },
    };
    function users_to_search_lookup(list: User[]): void {
        // Search in these objects first, then fetch from api
        const obj = STATE.all_fetched;
        list.forEach((u) => {
            obj.user_id[u.user_id] = u;
            obj.name[u.login.name] = u;
            if (u.login.mail) {
                obj.mail[u.login.mail] = u;
            }
        });
    }

    // #region Table
    const table_set_columns = (b: boolean) => {
        STATE.table.update_columns(b ? MOBILE_FILTER_HEADERS : []);
        STATE.table = STATE.table;
    };

    // #endregion
    const SEARCH_INPUT = {
        input_validation: (value: string) => {
            const input_text = value.trim().toLowerCase();
            search_input_element.value = input_text;
            const new_inputs: { [key in keyof typeof STATE.valid_inputs]: string } = {};
            STATE.valid_inputs = new_inputs;
            if (input_text.includes(" ") || STATE.invalid_inputs.includes(input_text)) {
                return;
            }
            if (STATE.exact_match) {
                if (input_text.length < 4) {
                    return;
                }
                if (input_text.includes("@")) {
                    if (validate_mail(input_text)) {
                        new_inputs.mail = input_text;
                    }
                } else {
                    if (validate_name_length(input_text)) {
                        new_inputs.name = input_text;
                    }
                    if (validate_guid(input_text, true)) {
                        new_inputs.user_id = input_text;
                    }
                }
            } else {
                if (input_text.includes("@")) {
                    if (input_text.match(/@/g)?.length === 1) {
                        new_inputs.mail = input_text;
                    }
                } else {
                    new_inputs.name = input_text;
                    if (validate_guid(input_text)) {
                        new_inputs.user_id = input_text;
                    }
                }
            }
        },
        clear_input: () => (STATE.valid_inputs = {}),
        fetch_search: async () => {
            if (is_obj_empty(STATE.valid_inputs)) {
                return;
            }
            STATE.has_searched = true;
            STATE.history_popup_visible = false;
            STATE.valid_inputs = {};
            const value = input_element.value;
            if (STATE.history.hasOwnProperty(value)) {
                STATE.table.replace_pages(STATE.history[value]);
                return;
            }
            const maps = STATE.all_fetched;
            let users: User[] = [];
            if (STATE.exact_match) {
                if (value.includes("@")) {
                    if (maps.mail.hasOwnProperty(value)) {
                        users.push(maps.mail[value]);
                    }
                } else {
                    if (validate_guid(value, true)) {
                        if (maps.user_id.hasOwnProperty(value)) {
                            users.push(maps.user_id[value]);
                        }
                    } else if (maps.name.hasOwnProperty(value)) {
                        users.push(maps.name[value]);
                    }
                }
            } else {
                const maplist = [maps.mail, maps.name];
                if (validate_guid(value)) {
                    maplist.push(maps.user_id);
                }
                for (const obj of maplist) {
                    Object.entries(obj).forEach(([str, user]) => {
                        if (str.includes(value)) {
                            users.push(user);
                        }
                    });
                }
            }
            if (!users.length) {
                const resp = await check_creds_then_fetch(`user/search/${value}?exact_match=${STATE.exact_match}`);
                if (!resp.ok) {
                    throw `Could not fetch search (Status: ${resp.status}): ${await resp.json()}`;
                }
                users = await resp.json();
                users_to_search_lookup(users);
            }
            const new_rows = convert_user_list_to_rows(users);
            STATE.table.replace_pages(new_rows);
            STATE.history[value] = new_rows;
            if (!new_rows.length) {
                STATE.not_found_str = value;
                STATE.invalid_inputs.push(value);
            }
        },
    };
    // #region Events
    is_mobile_view.subscribe((is_mobile) => table_set_columns(is_mobile));
    const on_key_down = (event: KeyboardEvent) => {
        if ((event.ctrlKey || event.metaKey) && event.key === "l") {
            event.preventDefault();
            search_input_element?.focus();
        } else if (event.key === "Escape") {
            STATE.history_popup_visible = false;
            STATE.selected_user = null;
            input_element?.blur();
        }
    };
    const close_search_history_popup = (event: Event) => {
        const tag = event.target as HTMLElement | null;
        if (tag) {
            if (contains(tag, ["input-container"])) {
                return;
            }
            STATE.history_popup_visible = false;
        }
    };
    // #endregion
    const delete_user = () => {
        // After delete_user is pressed, you have to confirm the deletion
        // TODO Fetch
    };
    // #endregion

    // Setup
    table_set_columns(get(is_mobile_view));
    $: input_is_valid = Object.keys(STATE.valid_inputs).length >= 1;
</script>

<svelte:window on:keydown={on_key_down} on:click={close_search_history_popup} />
<UserInfoModal bind:user={STATE.selected_user} bind:services_list={data.services} />

<div class="main">
    <div class="header">Search user</div>
    <div class="container">
        <div class="input-container">
            <div class="search-box">
                <SearchInput
                    placeholder={" Search by user, mail or ID"}
                    on_input_callback={SEARCH_INPUT.input_validation}
                    on_clear_callback={SEARCH_INPUT.clear_input}
                    on_input_enter={SEARCH_INPUT.fetch_search}
                    on_focus_callback={() => (STATE.history_popup_visible = true)}
                    --width="{SEARCH_BAR_WIDTH}px"
                />
                <MagnifyingGlass bind:valid={input_is_valid} callback={SEARCH_INPUT.fetch_search} />
            </div>
            {#if STATE.history_popup_visible}
                <!-- on_item_click_callback={search_history_btn_click} -->
                <HistoryPopup
                    on_click_callback={() => (STATE.history_popup_visible = false)}
                    bind:history={STATE.history}
                    bind:valid={input_is_valid}
                    --width="{SEARCH_BAR_WIDTH}px"
                />
            {/if}
        </div>
    </div>

    {#if !is_obj_empty(STATE.table.pages) || !STATE.has_searched}
        <Table state={STATE.table} />
        <!-- display_count={{ text: `user${data.total_users === 1 ? "" : "s"}`, count: data.total_users }} -->
    {:else}
        <div class="not-found">No user found: {STATE.not_found_str}</div>
    {/if}
</div>

<style>
    :global(.input-container) {
        --valid: #58be43;
        --valid-border: #619761e3;
        --invalid: #872929;
    }
    .main {
        display: flex;
        flex-direction: column;
        gap: 8px;
        width: 100%;
        margin: 12px;
    }
    .header {
        font-size: 32px;
    }

    .container {
        display: flex;
        flex-direction: row;
        justify-content: space-between;
        width: 100%;
        height: 60px;
        align-items: stretch;
        box-sizing: border-box;
    }
    .input-container {
        display: flex;
        flex-direction: column;
        justify-items: center;
    }
    .search-box {
        display: flex;
        padding-top: 12px;
        gap: 8px;
    }
    .not-found {
        border-radius: 20px;
        align-self: center;
        width: fit-content;
        padding: 10px;
        padding-top: 4px;
        background-color: rgb(207, 207, 207);
        border: 2px solid rgb(255, 255, 255);
        text-align: center;
        font-size: 40px;
        color: var(--invalid);
    }
</style>
