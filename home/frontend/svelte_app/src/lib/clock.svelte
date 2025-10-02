<script lang="ts">
    import { TimeSpec } from "./utils/const";
    import { datetime_localdate, datetime_utcnow } from "./utils/func";
    // https://stackoverflow.com/questions/29971898/how-to-create-an-accurate-timer-in-javascript
    const INTERVAL = 1000; // ms

    export let timespec: TimeSpec = TimeSpec.SECONDS;
    export let utc_date: boolean = true; // Else local date

    let dtfunc = utc_date ? datetime_utcnow : datetime_localdate;
    let time = clock(dtfunc());
    let expected = Date.now() + INTERVAL;

    const step = () => {
        var dt = Date.now() - expected; // the drift (positive for overshooting)
        if (dt > INTERVAL) {
            // something really bad happened. Maybe the browser (tab) was inactive?
            // possibly special handling to avoid futile "catch up" run
        }
        time = clock(dtfunc());
        expected += INTERVAL;
        setTimeout(step, Math.max(0, INTERVAL - dt)); // take into account drift
    };
    setTimeout(step, INTERVAL);

    // Return a string in the format of "HH:MM:SS:MS"
    function clock(time: Date): string {
        const timestr = time.toISOString().split("T")[1].replace("Z", "");
        switch (timespec) {
            case TimeSpec.MILLIS3:
                return timestr;
            case TimeSpec.SECONDS:
                return timestr.split(".")[0];
            case TimeSpec.MINUTES:
                return timestr.split(":").slice(0, 2).join(":");
        }
    }
</script>

{time}
