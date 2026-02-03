import axios from 'axios';
var qrcode = new QRCode("qrcode");
const fileURL = makeGetRequest();

function makeGetRequest(path) {
    axios.get(path).then(
        (response) => {
            var result = response.data;
            console.log(result);
        },
        (error) => {
            console.log(error);
        }
    );
}
makeGetRequest('http://10.23.230.15:5000');
function makeCode() {


    qrcode.makeCode(fileURL);
}

