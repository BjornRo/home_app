<script lang="ts">
    let sliding_div: HTMLDivElement;

    export let labels: { left: string; right: string };
    export let is_right: boolean = false;
    export let callback: (is_left: boolean) => void = () => {};
</script>

<button
    class="toggle-button"
    on:click={() => {
        is_right = !is_right;
        sliding_div.style.transform = `translateX(${is_right ? 100 : 0}%)`;
        callback(is_right);
    }}
>
    <div class="slot" bind:this={sliding_div} />
    {#each Object.entries(labels) as [key, name]}
        <span class="label {key}">{name}</span>
    {/each}
</button>

<style>
    .toggle-button {
        position: relative;
        width: var(--width, 200px);
        height: 50px;
        background: #bb7676;
        margin: 0;
        padding: 0;
        border: 3px solid #8f8f8f;
        border-radius: 16px;
        cursor: pointer;
        overflow: hidden;
    }
    .slot {
        position: absolute;
        top: 0;
        width: 50%;
        height: 100%;
        background-color: #26aa26;
        border: 3px solid #62c334;
        box-sizing: border-box;
        transition: transform 0.3s;
        border-radius: 12px;
    }
    .label {
        color: #221111;
        font-size: var(--font-size, 16px);
        position: absolute;
        width: 50%;
        top: 0;
        height: 100%;
        display: flex;
        justify-content: center;
        align-items: center;
    }

    .left {
        left: 0;
    }

    .right {
        right: 0;
    }
</style>
