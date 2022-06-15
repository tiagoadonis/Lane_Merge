function resetPressed() {
    var data = "Reset Pressed";
    $.post('/update_start_state', {"msg": data});
}