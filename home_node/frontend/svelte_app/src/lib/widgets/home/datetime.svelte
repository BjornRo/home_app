<script lang="ts" async>
    import { TimeSpec, day, months } from "$lib/utils/const";
    import Clock from "$lib/clock.svelte";
    import { datetime_localdate } from "$lib/utils/func";

    let dt = datetime_localdate();
    let current_time = get_items(dt);
    let time_offset = get_time_offset(dt);

    $: time_offset;
    $: current_time;

    const update_interval = 10_000; // Millis
    function get_time_offset(date: Date): string {
        return `0${Math.abs(date.getTimezoneOffset()) / 60}:00`;
    }
    function get_week(date: Date) {
        const jan1st = new Date(date.getFullYear(), 0, 1);
        const days2nextmon = jan1st.getDay() === 1 ? 0 : (7 - jan1st.getDay()) % 7;
        const nextmon = new Date(date.getFullYear(), 0, jan1st.getDate() + days2nextmon);
        if (date <= nextmon) {
            return date < nextmon ? 52 : 1;
        }
        return Math.ceil((date.getTime() - nextmon.getTime()) / (24 * 3600 * 1000) / 7);
    }

    function get_items(date: Date) {
        return {
            "Week day": day[date.getUTCDay()], // Date is adjusted for local. UTC is "local"
            Date: `${date.getUTCFullYear()} ${months[date.getUTCMonth()].substring(0, 3)} ${date.getUTCDate()}`,
            Week: get_week(date),
        };
    }

    (async () => {
        while (true) {
            await new Promise((resolve) => setTimeout(resolve, update_interval));
            dt = datetime_localdate();
            time_offset = get_time_offset(dt);
            current_time = get_items(dt);
        }
    })();
</script>

<div class="card root-card-borderradius">
    <div class="card-header">Current Time (UTC +{time_offset})</div>
    <div class="card-body">
        {#each Object.entries(current_time) as [key, value]}
            <div class="item {key.toLowerCase() === 'week' ? 'week' : ''}">
                <div class="item-key">{key}:</div>
                <div class="item-value">{value}</div>
            </div>
        {/each}
        <div class="item clock">
            <div class="item-key">Clock:</div>
            <div class="item-value">
                <Clock timespec={TimeSpec.SECONDS} utc_date={false} />
            </div>
        </div>
    </div>
</div>

<style>
    .week {
        /* flex-grow: 2; */
        max-width: 120px;
    }
    .clock {
        /* flex-grow: 2; */
        max-width: 150px;
    }
    .card-header {
        text-align: left;
        line-height: 1em;
        padding-left: 0.4em;
        padding-top: 0.3em;
        font-size: 1.6em;
        color: rgb(213, 212, 212);
        text-decoration: underline;
        text-decoration-thickness: 0.1em;
        text-decoration-color: rgb(94, 94, 94);
    }
    .card-body {
        display: flex;
        align-items: stretch;
        text-align: left;
        background: #237554;
        margin: 0.6em;
        padding-left: 0.1em;
        padding-right: 0.1em;
        border-radius: 0.5em;
        height: 100%;
        border: rgb(63, 63, 63) 0.2em solid;
    }
    .item {
        text-wrap: nowrap;
        flex: 1;
        display: flex;
        flex-direction: column;
        width: 120px;
        margin: 5px;
        padding-left: 0.2em;
        border-radius: 8px;
        background-color: #469273;
    }
    .item-key {
        text-decoration: underline;
        text-decoration-thickness: 0.1em;
        text-decoration-color: rgb(94, 94, 94);
        text-align: left;
        padding-top: 0.2em;
        padding-left: 0.3em;
        font-size: 1.5em;
        line-height: 1.2em;
    }
    .item-value {
        font-family: Arial, Helvetica, sans-serif;
        padding-top: 0.1em;
        padding-left: 0.4em;
        font-size: 1.7em;
        font-weight: bolder;
        color: rgb(204, 204, 204);
    }
    .card {
        display: flex;
        flex-direction: column;
        align-items: stretch;
        text-align: center;
        color: rgb(193, 193, 193);
        background: rgb(104, 142, 120);
        height: 142px;
    }
</style>
