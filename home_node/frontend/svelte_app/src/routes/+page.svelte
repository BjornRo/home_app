<script lang="ts" async>
    import Sensordata from "$lib/widgets/home/sensordata.svelte";
    import Datetimecard from "$lib/widgets/home/datetime.svelte";
    import Intervals from "$lib/widgets/home/intervals.svelte";
    // import Pyscriptcard from "$lib/widgets/home/pyscript.svelte";
    import { page } from "$app/stores";
    export let data;
</script>

<div class="main">
    <Datetimecard />
    <Sensordata data={data.sensor_data} />
    <!-- <Intervals /> -->
    <!-- <Pyscriptcard /> -->
</div>

<style>
    .main {
        display: flex;
        flex-direction: column;
        gap: 8px;
        width: 100%;
        margin: 12px;
    }
</style>
