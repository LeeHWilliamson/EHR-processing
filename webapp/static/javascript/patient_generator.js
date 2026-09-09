// document is a builtin javascript object for working with html doc currently loaded in browser
document
    .getElementById("patient-form") //find by htmlid
    /*
    .addEventListener registers listener for submit event on patient-form element
    then we use => to define a function
    */
    .addEventListener("submit", async (event) => { 
        event.preventDefault(); //tells browser to not refresh page when form submitted

        const body = { //getElementById get element objects representing element of id we passed
            //we make sure to convert strings to numbers as needed
            synthea_path: document.getElementById("synthea-path").value,
            count: Number(document.getElementById("count").value),
            state: document.getElementById("state").value,
            city: document.getElementById("city").value || null,
            min_age: Number(document.getElementById("min-age").value) || null,
            max_age: Number(document.getElementById("max-age").value) || null,
            keep_attribute: document.getElementById("keep-attribute").value || null,
        };

        //fetch is a browser api for making HTTP requests, we send one to our generate route here
        const response = await fetch("/generate", {
            method: "POST",
            //http requests contain headers, this header is telling FastAPI that we are sending a JSON
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(body) //convert javascript object to JSON
        });

        const result = await response.json(); //parse JSON response body to JavaScript object


        if (response.ok) {
            document.getElementById("result").textContent = "Patients generated!";
            await loadPatients();
        }
        else {
            document.getElementById("result").textContent = JSON.stringify(result);
        }
    });

async function loadPatients() {
    const response = await fetch("/patients");
    
    if (!response.ok) {
        console.error("Failed to load patients");
        return;
    }
    
    const patients = await response.json();

    const tileContainer = document.getElementById("patient-tiles");

    tileContainer.innerHTML = "";

    for (const patient of patients) {
        const tile = document.createElement("div");

        tile.className = "patient-tile";

        tile.innerHTML = `
            <h3>${patient.first_name} ${patient.last_name}</h3>
            <p>DOB: ${patient.dob}</p>
            <p>Gender: ${patient.gender}</p>
        
            <div class="patient-details">
                <p>Active Conditions: ${patient.conditions}</p>
                <p>Active Careplans: ${patient.careplans}</p>
                <p>Current Medications: ${patient.medications}</p>
                <p>Allergies: ${patient.allergies}</p>
            </div>
        `;

        tileContainer.appendChild(tile);
    }
}

// loadPatients();