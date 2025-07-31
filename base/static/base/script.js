// Global variables
let markers = []; // Array to hold markers shown on the map
let counters = []; // Global counters array
let geocoder; // For address search
let currentSelectedCounter = null;
let downloadInProgress = false; // Flag to prevent multiple downloads
let searchTimeout;
let selectedSearchIndex = -1;

// Initialize map
mapboxgl.accessToken = 'pk.eyJ1IjoidGNhcGVsMyIsImEiOiJjbWI5dTBkbGwwM2VsMmpuNnozYTR4c3c5In0.ExcltcyUTsype2FN-oSjnA';
const map = new mapboxgl.Map({
  container: 'map',
  style: 'mapbox://styles/mapbox/streets-v11',
  center: [-79, 35.7],
  zoom: 9
});

// Add navigation controls
map.addControl(new mapboxgl.NavigationControl());

// Initialize geocoder for address search
geocoder = new MapboxGeocoder({
  accessToken: mapboxgl.accessToken,
  mapboxgl: mapboxgl,
  countries: 'us',
  bbox: [-84.3219, 33.7529, -75.4606, 36.5880], // North Carolina bounds
  proximity: {
    longitude: -79,
    latitude: 35.7
  }
});

// Set bounds for North Carolina
map.on('load', () => {
  map.setMaxBounds([
    [-84.3219, 33.7529],
    [-75.4606, 36.5880]
  ]);
  
  // Add states layer
  map.addSource('states', {
    type: 'vector',
    url: 'mapbox://mapbox.us-states-v1'
  });
});

// Search functionality
function performSearch(query) {
  const searchResults = document.getElementById('searchResults');
  const clearButton = document.getElementById('searchClear');
  
  if (!query.trim()) {
    searchResults.classList.remove('show');
    clearButton.style.display = 'none';
    return;
  }

  clearButton.style.display = 'block';
  
  // Search through counters
  const counterResults = counters.filter(counter => 
    counter.counter_name.toLowerCase().includes(query.toLowerCase()) ||
    counter.counter_id.toString().includes(query) ||
    (counter.counter_notes && counter.counter_notes.toLowerCase().includes(query.toLowerCase())) ||
    (counter.vendor && counter.vendor.toLowerCase().includes(query.toLowerCase()))
  );

  let resultsHTML = '';
  
  // Add counter results
  counterResults.forEach((counter, index) => {
    resultsHTML += `
      <div class="search-result-item" data-type="counter" data-id="${counter.counter_id}" data-index="${index}">
        <div class="search-result-title">${counter.counter_name}</div>
        <div class="search-result-details">
          ID: ${counter.counter_id} | ${counter.vendor || 'Unknown vendor'}
          ${counter.counter_notes ? ' | ' + counter.counter_notes.substring(0, 50) + (counter.counter_notes.length > 50 ? '...' : '') : ''}
        </div>
      </div>
    `;
  });

  // Add address search option if the query looks like an address
  if (query.length > 3 && /[a-zA-Z]/.test(query)) {
    resultsHTML += `
      <div class="search-result-item" data-type="address" data-query="${query}" data-index="${counterResults.length}">
        <div class="search-result-title">Search "${query}" as address</div>
        <div class="search-result-details"></div>
      </div>
    `;
  }

  if (resultsHTML) {
    searchResults.innerHTML = resultsHTML;
    searchResults.classList.add('show');
    selectedSearchIndex = -1;
  } else {
    searchResults.innerHTML = '<div class="search-result-item"><div class="search-result-title">No results found</div></div>';
    searchResults.classList.add('show');
  }
}

function selectSearchResult(element) {
  const type = element.getAttribute('data-type');
  const searchBar = document.getElementById('searchBar');
  const searchResults = document.getElementById('searchResults');

  if (type === 'counter') {
    const counterId = parseInt(element.getAttribute('data-id'));
    const counter = counters.find(c => c.counter_id === counterId);
    
    if (counter) {
      // Zoom to counter
      map.easeTo({
        center: [counter.longitude, counter.latitude],
        zoom: 15,
        duration: 1000
      });

      // Show counter info
      showCounterInfo(counter);

      // Update search bar
      searchBar.value = counter.counter_name;
      
      // Highlight the marker
      highlightMarker(counter);
    }
  } 
  
  else if (type === 'address') {
    const query = element.getAttribute('data-query');
    
    // Use Mapbox Geocoding API
    geocoder.query(query);
    geocoder.on('result', function(e) {
      const result = e.result;
      map.easeTo({
        center: result.center,
        zoom: 14,
        duration: 1000
      });
      
      // Add a temporary marker for the address
      const addressMarker = new mapboxgl.Marker({color: 'red'})
        .setLngLat(result.center)
        .setPopup(new mapboxgl.Popup().setText(result.place_name))
        .addTo(map);
      
      // Remove the marker after 10 seconds
      setTimeout(() => {
        addressMarker.remove();
      }, 10000);
      
      searchBar.value = result.place_name;
    });
  }

  searchResults.classList.remove('show');
}

function highlightMarker(counter) {
  // Reset all markers first
  markers.forEach(marker => {
    const el = marker.getElement();
    el.style.width = '10px';
    el.style.height = '10px';
    el.style.backgroundColor = '#2C3E50';
    el.style.background = 'linear-gradient(135deg, #2C3E50 0%, #34495E 100%)';
  });

  // Find and highlight the specific marker
  const targetMarker = markers.find(marker => {
    const lngLat = marker.getLngLat();
    return Math.abs(lngLat.lng - counter.longitude) < 0.0001 && 
           Math.abs(lngLat.lat - counter.latitude) < 0.0001;
  });

  if (targetMarker) {
    const el = targetMarker.getElement();
    el.style.width = '20px';
    el.style.height = '20px';
    el.style.backgroundColor = '#C0392B';
    el.style.background = 'linear-gradient(135deg, #C0392B 0%, #E74C3C 100%)';
  }
}

function updateSearchSelection(items) {
  items.forEach((item, index) => {
    if (index === selectedSearchIndex) {
      item.classList.add('selected');
    } else {
      item.classList.remove('selected');
    }
  });
}

// Add counters to the map
function addCountersToMap() {
  counters.forEach(counter => {
    let el = document.createElement('div');
    el.className = 'marker';

    el.style.width = '10px';
    el.style.height = '10px';
    el.style.borderRadius = '50%';
    el.style.backgroundColor = '#2C3E50'; 
    el.style.background = 'linear-gradient(135deg, #2C3E50 0%, #34495E 100%)'; 
    el.style.border = 'none'; 
    el.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.2)'; 
    el.style.cursor = 'pointer'; 
   
    // Double click a counter to open the dashboard
    el.ondblclick = () => {
      const sensorId = Number(counter.counter_id);
      const url = `http://localhost:8088/superset/dashboard/p/1mGgqwnrz9A/?native_filters=(NATIVE_FILTER-_ox7CwuuBQK-dowCoOPTB:(__cache:(label:'${sensorId}',validateStatus:!f,value:!('${sensorId}')),extraFormData:(filters:!((col:counter_id,op:IN,val:!('${sensorId}')))),filterState:(label:'${sensorId}',validateStatus:!f,value:!('${sensorId}')),id:NATIVE_FILTER-_ox7CwuuBQK-dowCoOPTB,ownState:()))`;
      
      window.open(url, '_blank');
    };
   
    // Single click to select
    el.onclick = () => {
      // Reset markers
      markers.forEach(marker => {
        const markerEl = marker.getElement();
        markerEl.style.width = '10px';
        markerEl.style.height = '10px';
        markerEl.style.backgroundColor = '#2C3E50';
        markerEl.style.background = 'linear-gradient(135deg, #2C3E50 0%, #34495E 100%)';
      });

      el.style.width = '20px';
      el.style.height = '20px';
      el.style.backgroundColor = '#C0392B'; 
      el.style.background = 'linear-gradient(135deg, #C0392B 0%, #E74C3C 100%)'; 

      // Zoom to the marker location when clicked
      map.easeTo({
        center: [counter.longitude, counter.latitude], 
        zoom: 15, 
        duration: 1000, 
        easing: (t) => t 
      });

      // Option to download counts/datastreams
      currentSelectedCounter = counter;
      document.getElementById('downloadCountsBtn').style.display = 'block';

      showCounterInfo(counter);
    };

    // Create a marker and add it to the map
    let marker = new mapboxgl.Marker(el)
      .setLngLat([counter.longitude, counter.latitude])
      .setPopup(new mapboxgl.Popup().setText(counter.counter_name))
      .addTo(map);
   
    markers.push(marker);
  });
}

// Show counter information
function showCounterInfo(counter) {
  const infoPanel = document.getElementById('counterInfo');
  infoPanel.innerHTML = `
    <h3>${counter.counter_name}</h3>
    <p>ID: ${counter.counter_id}</p>
    <p>Latitude: ${counter.latitude.toFixed(4)}</p>
    <p>Longitude: ${counter.longitude.toFixed(4)}</p>
    <p>Vendor: ${counter.vendor}</p>
    <p>Counter notes: ${counter.counter_notes}</p>
  `;
  infoPanel.style.display = 'block';
}

// Download functionality
function downloadData(format) {
  const timestamp = new Date().toISOString().split('T')[0];
  let filename, content, mimeType;

  switch (format) {
    case 'json':
      filename = `nc_counters_${timestamp}.json`;
      content = JSON.stringify(counters, null, 2);
      mimeType = 'application/json';
      break;

    case 'csv':
      filename = `nc_counters_${timestamp}.csv`;
      content = convertToCSV(counters);
      mimeType = 'text/csv';
      break;

    default:
      console.error('Unknown format:', format);
      return;
  }

  // Create and trigger download
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  // Close download options
  document.getElementById('downloadOptions').classList.remove('show');
}

function convertToCSV(data) {
  if (!data || data.length === 0) return '';

  // Get all unique keys from all objects
  const keys = [...new Set(data.flatMap(Object.keys))];
  
  // Create header row
  const header = keys.join(',');
  
  // Create data rows
  const rows = data.map(item => {
    return keys.map(key => {
      let value = item[key];
      
      // Handle null/undefined values
      if (value === null || value === undefined) {
        value = '';
      }
      
      // Convert to string and escape quotes
      value = String(value).replace(/"/g, '""');
      
      // Wrap in quotes if contains comma, newline, or quote
      if (value.includes(',') || value.includes('\n') || value.includes('"')) {
        value = `"${value}"`;
      }
      
      return value;
    }).join(',');
  });

  return [header, ...rows].join('\n');
}

// Handle download for counts/datastreams
async function downloadCounterData() {
  if (!currentSelectedCounter || downloadInProgress) return;
  
  downloadInProgress = true;
  const counterId = currentSelectedCounter.counter_id;
  
  try {
    // Show the loading overlay
    const loadingOverlay = document.getElementById('loadingOverlay');
    loadingOverlay.style.display = 'flex';
    
    // Disable download buttons
    document.getElementById('downloadBtn').disabled = true;
    document.getElementById('downloadCountsBtn').disabled = true;
    
    // Fetch datastreams
    const datastreamsResponse = await fetch(`http://localhost:8000/counters/${counterId}/datastreams/`);
    const datastreamsData = await datastreamsResponse.json();
    
    // Extract datastream IDs
    const datastreamIds = datastreamsData.map(ds => ds.datastream_id);
    
    // Fetch counts for all datastreams
    const countsPromises = datastreamIds.map(datastreamId => 
      fetch(`http://localhost:8000/datastreams/${datastreamId}/counts`)
        .then(response => response.json())
        .then(counts => ({ datastreamId, counts }))
    );
    
    const allCountsResults = await Promise.all(countsPromises);
    
    // Combine all counts
    const allCounts = allCountsResults.flatMap(result => 
      result.counts.map(count => ({
        ...count,
        datastream_id: result.datastreamId
      }))
    );
    
    // Create zip file
    const zip = new JSZip();
    zip.file(`counter_${counterId}_datastreams.json`, JSON.stringify(datastreamsData, null, 2));
    zip.file(`counter_${counterId}_counts.json`, JSON.stringify(allCounts, null, 2));
    
    // Add separate files for each datastream
    allCountsResults.forEach(result => {
      zip.file(`counter_${counterId}_datastream_${result.datastreamId}_counts.json`, 
               JSON.stringify(result.counts, null, 2));
    });
    
    // Generate and download zip
    const content = await zip.generateAsync({ type: "blob" });
    const url = URL.createObjectURL(content);
    const a = document.createElement('a');
    a.href = url;
    a.download = `counter_${counterId}_data.zip`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
  } catch (error) {
    console.error('Download failed:', error);
    alert('Failed to download counter data');
  } finally {
    // Re-enable download buttons
    document.getElementById('downloadBtn').disabled = false;
    document.getElementById('downloadCountsBtn').disabled = false;
    
    // Hide loading overlay
    const loadingOverlay = document.getElementById('loadingOverlay');
    loadingOverlay.style.display = 'none';
    
    downloadInProgress = false;
  }
}

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
  // Fetch counters from the API
  fetch('http://localhost:8000/counters/')
    .then(response => {
      if (!response.ok) throw new Error('Not working');
      return response.json();
    })
    .then(data => {
      counters = data;
      addCountersToMap();
    })
    .catch(error => {
      console.error('Problem fetching counters:', error);
    });

  // Search event listeners
  document.getElementById('searchBar').addEventListener('input', function(e) {
    const query = e.target.value;
    
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      performSearch(query);
    }, 300);
  });

  // Keyboard navigation for search results
  document.getElementById('searchBar').addEventListener('keydown', function(e) {
    const searchResults = document.getElementById('searchResults');
    const items = searchResults.querySelectorAll('.search-result-item');
    
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      selectedSearchIndex = Math.min(selectedSearchIndex + 1, items.length - 1);
      updateSearchSelection(items);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      selectedSearchIndex = Math.max(selectedSearchIndex - 1, -1);
      updateSearchSelection(items);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (selectedSearchIndex >= 0 && items[selectedSearchIndex]) {
        selectSearchResult(items[selectedSearchIndex]);
      }
    } else if (e.key === 'Escape') {
      searchResults.classList.remove('show');
      selectedSearchIndex = -1;
    }
  });

  // Clear search functionality
  document.getElementById('searchClear').addEventListener('click', function() {
    const searchBar = document.getElementById('searchBar');
    const searchResults = document.getElementById('searchResults');
    const clearButton = document.getElementById('searchClear');
    
    searchBar.value = '';
    searchResults.classList.remove('show');
    clearButton.style.display = 'none';
    selectedSearchIndex = -1;
    
    // Reset all markers
    markers.forEach(marker => {
      const el = marker.getElement();
      el.style.width = '10px';
      el.style.height = '10px';
      el.style.backgroundColor = '#2C3E50';
      el.style.background = 'linear-gradient(135deg, #2C3E50 0%, #34495E 100%)';
    });
    
    // Hide counter info
    document.getElementById('counterInfo').style.display = 'none';
  });

  // Click outside to close search results
  document.addEventListener('click', function(e) {
    const searchContainer = document.querySelector('.search-wrapper');
    const searchResults = document.getElementById('searchResults');
    
    if (!searchContainer.contains(e.target)) {
      searchResults.classList.remove('show');
      selectedSearchIndex = -1;
    }
  });

  // Handle clicks on search results
  document.addEventListener('click', function(e) {
    if (e.target.closest('.search-result-item')) {
      selectSearchResult(e.target.closest('.search-result-item'));
    }
  });

  // Click outside to close counter info
  document.addEventListener('click', (event) => {
    const infoPanel = document.getElementById('counterInfo');
    const markersContainer = document.querySelectorAll('.marker');
    const searchContainer = document.querySelector('.search-wrapper');
    const downloadContainer = document.querySelector('.download-container');
    
    const clickedInsidePanel = infoPanel.contains(event.target);
    const clickedInsideMarker = Array.from(markersContainer).some(marker =>
      marker.contains(event.target)
    );
    const clickedInsideSearch = searchContainer.contains(event.target);
    const clickedInsideDownload = downloadContainer.contains(event.target);

    if (!clickedInsidePanel && !clickedInsideMarker && !clickedInsideSearch && !clickedInsideDownload) {
      infoPanel.style.display = 'none';
      
      if(!downloadInProgress){
        currentSelectedCounter = null;
        document.getElementById('downloadCountsBtn').style.display = 'none';
      }
      
      // Reset all markers
      markers.forEach(marker => {
        const el = marker.getElement();
        el.style.width = '10px';
        el.style.height = '10px';
        el.style.backgroundColor = '#2C3E50';
        el.style.background = 'linear-gradient(135deg, #2C3E50 0%, #34495E 100%)';
      });
    }
  });

  // Download event listeners
  document.getElementById('downloadBtn').addEventListener('click', function(e) {
    e.stopPropagation();
    const options = document.getElementById('downloadOptions');
    options.classList.toggle('show');
  });

  document.querySelectorAll('.download-option').forEach(option => {
    option.addEventListener('click', function(e) {
      e.stopPropagation();
      const format = this.getAttribute('data-format');
      downloadData(format);
    });
  });

  document.getElementById('downloadCountsBtn').addEventListener('click', downloadCounterData);
});