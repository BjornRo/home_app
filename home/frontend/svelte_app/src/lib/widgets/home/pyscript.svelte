<script lang="ts">
    export const csr = true;
    export const ssr = false;
</script>

<svelte:head>
    <link rel="stylesheet" href="https://pyscript.net/releases/2024.6.2/core.css" />
    <script type="module" src="https://pyscript.net/releases/2024.6.2/core.js"></script>
</svelte:head>

<div class="main root-card-borderradius">
    <script type="py" terminal worker>
        __terminal__.resize(10,12);
        import code;
        code.interact();
    </script>
</div>

<style>
    .boo {
        width: 200px;
    }
    .main {
        display: flex;
        flex-direction: column;
        justify-content: center;
        padding: 5px;
        border-radius: 0.5em;
        border: 2px solid red;
        height: 250px;
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
</style>
