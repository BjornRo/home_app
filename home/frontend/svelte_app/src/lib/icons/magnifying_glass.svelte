<script lang="ts">
    export let valid: boolean;
    export let callback: () => Promise<void>;
</script>

<button class="magnifying-glass" disabled={!valid} on:click={callback}>
    <p class="frame" class:ok={valid} />
    <p class="handle" class:ok={valid} />
</button>

<style>
    .magnifying-glass {
        zoom: 0.9;
        cursor: pointer;
        border: none;
        display: flex;
        border-radius: 10px;
        padding: 2px;
        margin-top: -4px;
        padding-left: 12px;
        padding-right: 12px;
        border: var(--invalid) 4px solid;
        transition: 0.4s;
        background: #396c4c;
        border-color: var(--valid-border);
        filter: none;
    }
    .magnifying-glass:disabled {
        cursor: default;
        border: var(--invalid) 4px solid;
        filter: brightness(1.2) saturate(0.2) contrast(40%);
    }

    .magnifying-glass:not:disabled:hover {
        transition: 0.4s;
        background: #9192ba;
    }
    .frame {
        margin: 0;
        padding: 0;
        margin: 2px 4px 8px 2px;
        width: 17px;
        aspect-ratio: 1;
        border-radius: 50%;
        border: 5px solid var(--invalid);
        transition: 0.4s;
    }
    .handle {
        margin: 0;
        padding: 0;
        padding-bottom: 2px;
        width: 6px;
        height: 16px;
        border-radius: 10px;
        background-color: var(--invalid);
        transform: translate(-6px, 19px) rotate(-45deg);
        transition: 0.4s;
    }
    .frame.ok {
        border-color: var(--valid);
        transition: 0.4s;
    }
    .handle.ok {
        background-color: var(--valid);
        transition: 0.4s;
    }
</style>
