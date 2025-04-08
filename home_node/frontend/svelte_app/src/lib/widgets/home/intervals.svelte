<script lang="ts">
    let background_color = "";
    // Return a string in the format of "HH:MM:SS:MS"
    function format_time_ms(milliseconds: number): string {
        let seconds = Math.floor(milliseconds / 1000);
        let minutes = Math.floor(seconds / 60);
        milliseconds = milliseconds % 1000;
        seconds = seconds % 60;
        minutes = minutes % 60;
        return `${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}.${milliseconds
            .toString()
            .slice(0, 1)}`;
    }

    async function countdown(time: number) {
        const tick = 100;
        run_time = format_time_ms(time);
        while (0 < time) {
            await new Promise((resolve) => setTimeout(resolve, tick));
            time -= tick;
            run_time = format_time_ms(time);
        }
        run_time = format_time_ms(0);
    }

    async function train_interval(intervals: number | null, length: number | null, pause: number | null) {
        if (intervals === null || length === null || pause === null) {
            return null;
        }
        toggleVisible();
        let tmp_background = background_color;
        background_color = "darkgreen";

        // Convert from sec to ms.
        length *= 1000;
        pause *= 1000;
        for (let i = 0; i < intervals; i++) {
            state = "running";
            curr_interval = `${i + 1}/${intervals}`;
            await countdown(length);
            if (i === intervals - 1) {
                break;
            }
            state = "pause";
            await countdown(pause);
        }
        state = "youre done! well done!";
        await new Promise((resolve) => setTimeout(resolve, 4000));
        toggleVisible();
        reset_state();
        background_color = tmp_background;
    }

    function reset_state() {
        state = "stopped";
        curr_interval = "0/0";
        run_time = format_time_ms(0);
    }

    function toggleVisible() {
        visible = !visible;
    }

    let state = "stopped";
    let curr_interval = "0/0";
    let run_time = format_time_ms(0);
    let visible = true;
</script>

<div class="main root-card-borderradius">
    <div class="btn-group">
        <button
            class="btn active"
            on:click={() => {
                train_interval(4, 2, 4);
            }}
        >
            <div class="icon">
                <div class="icon-stop" />
            </div>
        </button>
        <button
            class="btn inactive"
            on:click={() => {
                train_interval(4, 2, 4);
            }}
        >
            <div class="icon">
                <div class="icon-start" />
                <div class="icon-pause" />
            </div>
        </button>
    </div>
    <div class="info">
        <div class="info-item">State: {state}</div>
        <div class="info-item">Interval: {curr_interval}</div>
        <div class="info-item">Time: {run_time}</div>
    </div>
</div>

<style>
    :disabled {
        background-color: #564848 !important;
    }
    .active {
        background-color: #c03939;
    }

    .btn-group {
        display: flex;
        margin: 0;
        flex-direction: row;
        gap: 12px;
        margin: 6px;
    }

    .inactive {
        background-color: #49c360;
    }

    .btn {
        display: flex;
        border: none;
        font-size: 30px;
        font-weight: bold;
        justify-content: center;
        align-items: center;
        width: 100px;
        height: 70px;
        border-radius: 20px;
        box-shadow: 1;
        box-shadow: 0 0 10px rgba(0, 0, 0, 0.706);
        transition: background-color 0.2s ease, border-radius 0.5s ease;
    }
    .btn:hover {
        background-color: #36acac9e;
        border-radius: 12px;
    }
    .main {
        display: flex;
        flex-direction: column;
        /* flex-wrap: wrap; */
        justify-content: center;
        padding: 5px;
        border-radius: 0.5em;
        border: 2px solid red;
        background-color: rgb(182, 141, 91);
    }
    .info {
        background-color: grey;
        border: 2px solid orange;
        display: flex;
        flex-direction: column;
        width: 200px;
        height: 200px;
    }
    .info-item {
        text-align: center;
        background: rgb(182, 140, 0);
        width: 10em;
        border-radius: 0.5em;
        margin: 4px;
    }
    .icon {
        display: flex;
        flex-direction: row;
        width: max-content;
        height: max-content;
        zoom: 0.55;
        border-radius: 15px;
        padding: 10px;
    }
    .icon-start {
        border-style: solid;
        box-sizing: border-box;
        width: 60px;
        height: 80px;
        border-width: 40px 0px 40px 60px;
        border-color: transparent transparent transparent #202020;
    }
    .icon-pause {
        border-style: solid;
        box-sizing: border-box;
        width: 40px;
        height: 80px;
        border-style: double;
        border-width: 0px 0px 0px 40px;
        border-color: #202020;
    }
    .icon-stop {
        border-style: solid;
        box-sizing: border-box;
        width: 60px;
        height: 60px;
        border-radius: 8px;
        background-color: black;
    }
</style>
