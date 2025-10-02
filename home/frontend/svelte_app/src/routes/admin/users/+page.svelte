<script lang="ts" async>
    import { type User } from "$lib/utils/const";
    import { is_mobile_view } from "$lib/utils/stores";
    import { check_creds_then_fetch } from "$lib/utils/func";
    import { get } from "svelte/store";
    import UserInfoModal from "./user_info_modal.svelte";
    import { type Pages, type Row, TableState } from "$lib/table";
    import Table from "$lib/table.svelte";
    import { toast } from "$lib/toast_notification.svelte";
    import { convert_user_list_to_rows } from "$lib/admin/user_utils";

    export let data;

    type HeaderKeys = keyof typeof data.headers;

    const STATE = {
        table: new TableState<HeaderKeys, User>(
            data.rows_per_page,
            data.headers,
            "total",
            data.users_count,
            (user) => (STATE.selected_user = user),
            fetch_offset
        ),
        selected_user: null as User | null,
    };

    // #region Table
    const table_set_columns = (b: boolean) => {
        STATE.table.update_columns(b ? data.headers_filter : []);
        STATE.table = STATE.table;
    };
    async function fetch_offset(offset: number) {
        const resp = await check_creds_then_fetch(`user?limit=${data.rows_per_page}&offset=${offset}`);
        if (!resp.ok) {
            throw `Could not fetch new page (Status: ${resp.status}): ${await resp.json()}`;
        }
        const new_rows: User[] = await resp.json();
        return convert_user_list_to_rows(new_rows);
    }
    // #endregion

    // #region Events
    is_mobile_view.subscribe((is_mobile) => table_set_columns(is_mobile));

    const delete_user = () => {
        // After delete_user is pressed, you have to confirm the deletion
        // TODO Fetch
    };
    // #endregion

    STATE.table.init(convert_user_list_to_rows(data.users));
    table_set_columns(get(is_mobile_view));
</script>

<UserInfoModal bind:user={STATE.selected_user} bind:services_list={data.services} />

<div class="main">
    <div class="header">All users</div>
    <Table state={STATE.table} />
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
</style>
