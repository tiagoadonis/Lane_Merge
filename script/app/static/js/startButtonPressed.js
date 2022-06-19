var count = 0;

function startPressed() {
    var data = "Start Pressed";
    count++; 
    $.post('/update_start_state', {"msg": data, "count": count});
}