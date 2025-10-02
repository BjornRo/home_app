// import * as store from '$app/stores';
import type { PageServerLoad } from "./$types";
import { get_sensor_data } from "$lib/utils/func";
import type { SensorData } from "$lib/utils/const";
import type { ServerLoadEvent } from "@sveltejs/kit";

const CACHE_DURATION = 10000;
let sensor_cache_data: null | SensorData = null;
let sensor_cache_ts = 0;

const get_set_cache = async (event: ServerLoadEvent) => {
    const datenow = Date.now();
    if (datenow - sensor_cache_ts >= CACHE_DURATION) {
        sensor_cache_data = await get_sensor_data(event.fetch);
        sensor_cache_ts = datenow;
    }
    return sensor_cache_data;
};

export const load: PageServerLoad = async (event) => {
    return { sensor_data: await get_set_cache(event) };
};
