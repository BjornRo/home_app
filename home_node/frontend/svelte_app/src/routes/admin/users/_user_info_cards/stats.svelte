<script lang="ts">
    import type { User, Acl } from "$lib/utils/const";
    import { capitalize, is_isodate, is_arr, is_obj, is_str, rwx_num_to_str } from "$lib/utils/func";

    export let user: User;
    const FILTER_KEYS = ["user_id", "login", "roles", "acl"];

    function* zip(...iterables: any[]) {
        let iterators = iterables.map((i) => i[Symbol.iterator]());
        while (true) {
            let results = iterators.map((iter) => iter.next());
            if (results.some((res) => res.done)) return;
            else yield results.map((res) => res.value);
        }
    }
    const cast_acl = (val: any) => val as Acl;
    const format_obj_value = (s: any) => {
        if (typeof s === "string" && is_isodate(s)) {
            const parts = s.split(".");
            if (parts.length !== 1 && parts[1].length > 4) {
                if (parts[1].endsWith("Z")) {
                    parts[1] = parts[1].slice(0, -1);
                }
                parts[1] = parseFloat(`0.${parts[1]}`).toFixed(3).split(".")[1];
                return parts.join(".") + "Z";
            }
        }
        return s;
    };
</script>

<div class="main">
    <div class="header">
        <p>Info</p>
    </div>
    <div class="content">
        {#each Object.entries(user).filter(([k]) => !FILTER_KEYS.includes(k.toLowerCase())) as [key, value]}
            <div class="item">
                <div class="item-key">
                    {capitalize(key).replace("_", " ")}
                    {#if key === "registration"}
                        <div class="read-only">(read-only)</div>
                    {/if}
                </div>
                <div class="item-value">
                    {#if is_str(value)}
                        {#if is_isodate(value)}
                            {#each zip(["datetop", "datebottom"], value.split("T", 2)) as [cls, val]}
                                <div class={cls}>
                                    {val}
                                </div>
                            {/each}
                        {:else}
                            {value}
                        {/if}
                    {:else if is_arr(value)}
                        {"["}
                        {#each value as obj}
                            {#if is_obj(obj)}
                                {#if key === "acl"}
                                    {#each [cast_acl(obj)] as { resource, rwx }}
                                        <div class="obj-keyval" style="margin-left: 10px;">
                                            <div class="obj-key">
                                                <div class="obj-key-pfx">{resource}</div>
                                                :
                                            </div>
                                            <div style="margin-right: 4px;">
                                                {rwx_num_to_str(rwx)}
                                            </div>
                                        </div>
                                    {/each}
                                {/if}
                            {/if}
                        {/each}
                        {"]"}
                    {:else if is_obj(value)}
                        {#each Object.entries(value) as [k, v]}
                            <div class="obj-keyval">
                                <div class="obj-key">
                                    <div class="obj-key-pfx">
                                        {k}
                                    </div>
                                    :
                                </div>
                                {format_obj_value(v)}
                            </div>
                        {/each}
                    {/if}
                </div>
            </div>
        {/each}
    </div>
</div>

<style>
    p {
        margin: 4px;
        margin-bottom: 0px;
        font-size: 20px;
        padding: 0;
    }
    .read-only {
        align-self: center;
        margin-left: 6px;
        font-size: 14px;
    }
    .obj-keyval {
        display: flex;
        flex-direction: row;
        gap: 4px;
        font-size: 16px;
    }
    .obj-key {
        display: flex;
    }
    .obj-key-pfx {
        border-bottom: #6377d17c 2px solid;
    }

    .main {
        border: 3px solid rgb(117, 112, 206);
        border-radius: 6px;
        background-color: #d2dee9;
        display: flex;
        flex-direction: column;
        flex-wrap: wrap;
    }
    .header {
        display: flex;
        flex-direction: row;
    }
    .content {
        display: flex;
        flex-direction: row;
        flex-wrap: wrap;
        justify-content: flex-start;
        margin: 4px;
        padding-right: 6px;
        padding-top: 3px;
        padding-bottom: 3px;
        display: flex;
        border-radius: 4px;
        border: 2px solid rgba(119, 145, 231, 0.869);
        box-shadow: inset 0 0 4px rgba(202, 81, 81, 0.5);
    }
    .item {
        display: flex;
        flex-direction: column;
        margin-top: 4px;
        margin-bottom: 4px;
        margin-left: 8px;
        border-radius: 6px;
        box-shadow: inset 0 0 4px rgba(127, 127, 166, 0.5);
        padding: 5px;
        border: 2px solid #5d70c5;
    }
    .item-key {
        display: flex;
        font-size: 18px;
    }
    .item-value {
        font-size: 14px;
    }
    .datetop {
        font-size: 17px;
    }
    .datebottom {
        font-size: 15px;
    }
</style>
