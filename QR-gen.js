import axios from 'axios';
var qrcode = new QRCode("qrcode");
const fileURL = makeGetRequest();

function buildValidatedUrl(baseUrl) {
    try {
        // Minimal path validation
        if (baseUrl.includes('/../') || /\/%2e%2e\//i.test(baseUrl)) {
            throw new Error('Invalid path');
        }
        
        const url = new URL(baseUrl);
        
        // Protocol + host checks
        const allowedDomains = ['10.23.230.15']; // add your allowed domains here
        if (!allowedDomains.includes(url.hostname)) {
            throw new Error('Invalid host');
        }
        if (!['http:', 'https:'].includes(url.protocol)) {
            throw new Error('Invalid protocol');
        }
        
        return url.href;
    } catch {
        throw new Error('Invalid URL');
    }
}

function makeGetRequest(path) {
    const validatedUrl = buildValidatedUrl(path);
    axios.get(validatedUrl).then(
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

