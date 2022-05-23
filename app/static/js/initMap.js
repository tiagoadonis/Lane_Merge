function initMap(obu1_title) {
    console.log("OBU 1 title: "+obu1_title)

    map = new google.maps.Map(document.getElementById("map"), {
        zoom: 20,
        center: {lat: 40.640259, lng: -8.663455},
        mapTypeId: "satellite",
    });
    
    // Create an info window to share between markers.
    const infoWindow = new google.maps.InfoWindow();

    // RSU 
    const rsu = new google.maps.Marker({
        position: new google.maps.LatLng(40.640585, -8.663218),
        map: map,
        icon: {
            url: "static/rsu.png",
            scaledSize: new google.maps.Size(60, 60)
        },
        title: "RSU",
    });

    rsu.addListener("click", () => {
        infoWindow.close();
        infoWindow.setContent(rsu.getTitle());
        infoWindow.open(rsu.getMap(), rsu);
    });

    // OBU 1 
    const obu_1 = new google.maps.Marker({
        position: new google.maps.LatLng(40.640375, -8.663347),
        map: map,
        icon: {
            url: "static/vehicle_4.png",
            scaledSize: new google.maps.Size(50, 50)
        },
        //title: "OBU_1",
        title: obu1_title,
    });

    obu_1.addListener("click", () => {
        infoWindow.close();
        infoWindow.setContent(obu_1.getTitle());
        infoWindow.open(obu_1.getMap(), obu_1);
    });

    // OBU 2
    const obu_2 = new google.maps.Marker({
        position: new google.maps.LatLng(40.640535, -8.663015),
        map: map,
        icon: {
            url: "static/vehicle_5.png",
            scaledSize: new google.maps.Size(50, 50)
        },
        title: "OBU_2",
    });

    obu_2.addListener("click", () => {
        infoWindow.close();
        infoWindow.setContent(obu_2.getTitle());
        infoWindow.open(obu_2.getMap(), obu_2);
    });

    // OBU 3
    const obu_3 = new google.maps.Marker({
        position: new google.maps.LatLng(40.640234, -8.663464),
        map: map,
        icon: {
            url: "static/vehicle_2.png",
            scaledSize: new google.maps.Size(50, 50)
        },
        title: "OBU_3",
    });

    obu_3.addListener("click", () => {
        infoWindow.close();
        infoWindow.setContent(obu_3.getTitle());
        infoWindow.open(obu_3.getMap(), obu_3);
    });

    // OBU 4
    const obu_4 = new google.maps.Marker({
        position: new google.maps.LatLng(40.640422, -8.663217),
        map: map,
        icon: {
            url: "static/vehicle_3.png",
            scaledSize: new google.maps.Size(50, 50)
        },
        title: "OBU_4",
    });

    obu_4.addListener("click", () => {
        infoWindow.close();
        infoWindow.setContent(obu_4.getTitle());
        infoWindow.open(obu_4.getMap(), obu_4);
    });

    // OBU 5
    const obu_5 = new google.maps.Marker({
        position: new google.maps.LatLng(40.640093, -8.663590),
        map: map,
        icon: {
            url: "static/vehicle_1.png",
            scaledSize: new google.maps.Size(50, 50)
        },
        title: "OBU_5",
    });

    obu_5.addListener("click", () => {
        infoWindow.close();
        infoWindow.setContent(obu_5.getTitle());
        infoWindow.open(obu_5.getMap(), obu_5);
    });
} 