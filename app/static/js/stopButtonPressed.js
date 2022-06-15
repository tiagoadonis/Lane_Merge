function stopPressed() {
    var data = "Stop Pressed";
    $.post('/update_start_state', {"msg": data});
}