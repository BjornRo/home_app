<script lang="ts" async>
    import { page } from "$app/stores";
    import { get_sensor_data } from "$lib/utils/func";
    import { type Device, type LocationData, type SensorData } from "$lib/utils/const";

    export let data: SensorData | null = null;

    interface ModifiedLocationData {
        [k: string]: Device | null;
    }

    const name_mapping = { bikeroom: "Outdoor", kitchen: "Kitchen", balcony: "Balcony" };
    let home_data: ModifiedLocationData = reshape_data(data?.home ?? {}, name_mapping);
    $: home_data = home_data;
    const update_interval = 60_000;

    function reshape_data(loc_data: LocationData, rename_map: Object): ModifiedLocationData {
        return Object.fromEntries(
            Object.entries(rename_map).map(([name, new_name]) => {
                if (name in loc_data) {
                    const device_data: Device = loc_data[name];
                    return [new_name, device_data];
                }
                return [new_name, null];
            })
        );
    }
    // const loc_data: LocationData = Object.fromEntries(
    //     Object.entries(resp.home).sort(([keyA], [keyB]) => keyA.localeCompare(keyB))
    // );

    (async () => {
        while (true) {
            await new Promise((resolve) => setTimeout(resolve, update_interval));
            const resp = await get_sensor_data(null);
            if (resp) {
                home_data = reshape_data(resp.home, name_mapping);
            }
        }
    })();
</script>

<div class="card root-card-borderradius">
    {#each Object.entries(home_data) as [device_name, device_data]}
        <div class="card-child">
            <div class="card-header">{device_name}</div>
            <div class="card-body">
                <div class="item-top-name">Temperature:</div>
                <div class="item-top-value">{device_data?.data.temperature.toFixed(2) ?? "N/A"}°C</div>
                {#if device_data?.data.humidity}
                    <div class="item-container">
                        <div class="item-name">Humidity:</div>
                        <div class="item-value">{device_data.data.humidity.toFixed(2)}%</div>
                    </div>
                {/if}
                {#if device_data?.data.airpressure}
                    <div class="item-container">
                        <div class="item-name">Airpressure:</div>
                        <div class="item-value">{device_data.data.airpressure.toFixed(2)}hPa</div>
                    </div>
                {/if}
                <div class="footer">Date: {device_data?.date.replace("T", " ")}</div>
            </div>
        </div>
    {/each}
</div>

<style>
    .card {
        display: flex;
        justify-content: space-between;
        flex-direction: row;
        /* flex-wrap: wrap; */
        align-items: stretch;
        padding: 0.5em;
        gap: 0.5em;
        background: #797193;
        height: 12em;
    }
    .card-child {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: stretch;
        text-align: center;
        color: rgb(193, 193, 193);
        background: rgb(39, 38, 77);
        border-radius: 0.5em;
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
        flex-direction: column;
        text-align: left;
        background: #40375e;
        margin: 0.6em;
        box-sizing: border-box;
        border-radius: 0.5em;
        height: 100%;
        border: rgb(63, 63, 63) 0.2em solid;
    }
    .item-top-name {
        text-decoration: underline;
        text-decoration-thickness: 0.1em;
        text-decoration-color: rgb(94, 94, 94);
        text-align: left;
        padding-top: 0.2em;
        padding-left: 0.3em;
        font-size: 1.2em;
        line-height: 1.2em;
    }
    .item-top-value {
        font-family: Arial, Helvetica, sans-serif;
        padding-top: 0.1em;
        padding-left: 0.4em;
        font-size: 1.5em;
        font-weight: bolder;
        color: rgb(204, 204, 204);
    }
    .item-container {
        display: flex;
        justify-content: space-between;
        width: 100%;
        padding-top: 0.1em;
        align-items: center;
        flex-direction: row;
    }
    .item-name {
        text-decoration: underline;
        text-decoration-thickness: 0.1em;
        text-decoration-color: rgb(94, 94, 94);
        text-align: left;
        font-size: 1.1em;
        padding-top: 0.1em;
        padding-left: 0.5em;
        line-height: 1.3em;
        float: left;
    }
    .item-value {
        font-family: Arial, Helvetica, sans-serif;
        padding-top: 0.1em;
        padding-left: 0.4em;
        padding-right: 0.3em;
        font-size: 1.2em;
        line-height: 1.1em;
        font-weight: bolder;
        color: rgb(204, 204, 204);
    }
    .footer {
        margin-top: auto;
        padding-bottom: 0.1em;
        padding-left: 0.5em;
        font-size: 0.9em;
        color: #797193;
    }
</style>
