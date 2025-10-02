<div class="container">
    <div class="close-icon" />
</div>

<style>
    .container {
        width: 32px;
        height: 32px;
        border-radius: 10px;
        outline: 0;
        border: 2px solid #00000084;
        background: #eeeeee;
        transition: 0.3s;
    }
    .container:hover {
        background: #b7a4a47e;
    }
    .close-icon::before,
    .close-icon::after {
        content: "";
        top: 18px;
        left: 8px;
        position: absolute;
        width: 20px;
        height: 4px;
        border-radius: 20px;
        background-color: #333333;
        transform: translateY(-50%) rotate(45deg);
    }
    .close-icon::after {
        transform: translateY(-50%) rotate(-45deg);
    }
</style>
