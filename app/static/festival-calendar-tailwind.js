class FestivalCalendar {
    constructor(selector, options) {
        this.container = document.querySelector(selector);
        if (!this.container) {
            console.error(`Container element "${selector}" not found.`);
            return;
        }

        this.options = Object.assign({
            scenes: [],
            events: [],
            pixelsPerHour: 100,
            dayStartTime: null, 
            dayEndTime: null,   
            timeFormat: { hour: '2-digit', minute: '2-digit', hour12: false }
        }, options);
        
        this.resolveDayBoundaries();
        this.initModal(); // Initialiser modal event listeners
    }

    initModal() {
        this.modalOverlay = document.getElementById('event-modal-overlay');
        this.modalContent = document.getElementById('event-modal-content');
        this.modalTitle = document.getElementById('modal-title');
        this.modalTime = document.getElementById('modal-time');
        this.modalScene = document.getElementById('modal-scene');
        this.modalRisk = document.getElementById('modal-risk');
        this.modalDescription = document.getElementById('modal-description');
        const closeButton = document.getElementById('modal-close-button');

        if (this.modalOverlay && closeButton) {
            closeButton.addEventListener('click', () => this.hideModal());
            this.modalOverlay.addEventListener('click', (event) => {
                if (event.target === this.modalOverlay) { // Luk kun hvis der klikkes på overlay, ikke content
                    this.hideModal();
                }
            });
        } else {
            console.warn("Modal elements not found in the DOM.");
        }
    }

    showModal(eventData) {
        if (!this.modalOverlay) return;

        const sceneName = this.options.scenes.find(s => FestivalCalendar.slugify(s.name) === FestivalCalendar.slugify(eventData.sceneId))?.name || 'Ukendt scene';
        const startTime = new Date(eventData.startTime);
        const endTime = eventData.endTime ? new Date(eventData.endTime) : new Date(startTime.getTime() + 60*60*1000);

        this.modalTitle.textContent = eventData.title;
        this.modalTime.textContent = `${this.formatTime(startTime)} - ${this.formatTime(endTime)}`;
        this.modalScene.textContent = sceneName;
        
        let riskText = 'Ukendt';
        let riskColorClass = 'text-slate-500'; 
        switch (eventData.riskLevel?.toLowerCase()) {
            case 'high': riskText = 'Høj'; riskColorClass = 'text-red-600'; break;
            case 'medium': riskText = 'Mellem'; riskColorClass = 'text-yellow-600'; break;
            case 'low': riskText = 'Lav'; riskColorClass = 'text-green-600'; break;
        }
        this.modalRisk.textContent = riskText;
        this.modalRisk.className = `font-semibold ${riskColorClass}`;

        // Populate risk assessment details
        const modalRemarks = document.getElementById('modal-remarks');
        const modalCrowdProfile = document.getElementById('modal-crowd-profile');
        const modalNotes = document.getElementById('modal-notes');

        if (modalRemarks) {
            modalRemarks.innerHTML = eventData.remarks ? 
                eventData.remarks : 
                '<span class="text-gray-400 italic">N/A</span>';
        }

        if (modalCrowdProfile) {
            modalCrowdProfile.innerHTML = eventData.crowdProfile ? 
                eventData.crowdProfile : 
                '<span class="text-gray-400 italic">N/A</span>';
        }

        if (modalNotes) {
            modalNotes.innerHTML = eventData.notes ? 
                eventData.notes : 
                '<span class="text-gray-400 italic">N/A</span>';
        }

        this.modalDescription.textContent = eventData.description || 'Ingen beskrivelse tilgængelig.';
        
        this.modalOverlay.classList.remove('hidden'); 
        document.body.style.overflow = 'hidden'; 
    }

    hideModal() {
        if (!this.modalOverlay) return;
        this.modalOverlay.classList.add('hidden'); 
        document.body.style.overflow = ''; 
    }

    static slugify(str) {
        return str
            .toLowerCase()
            .replace(/å/g, 'a')
            .replace(/ø/g, 'o')
            .replace(/æ/g, 'ae')
            .replace(/[^a-z0-9]+/g, '-')
            .replace(/(^-|-$)/g, '');
    }

    resolveDayBoundaries() {
        // ... (samme som før)
        if (this.options.dayStartTime && this.options.dayEndTime) {
            const [startH, startM] = this.options.dayStartTime.split(':').map(Number);
            const [endH, endM] = this.options.dayEndTime.split(':').map(Number);
            let refDateStr = new Date().toISOString().split('T')[0];
            if (this.options.events.length > 0 && this.options.events[0].startTime) {
                try {
                    const eventDate = new Date(this.options.events[0].startTime);
                    if (!isNaN(eventDate)) { refDateStr = eventDate.toISOString().split('T')[0]; }
                } catch (e) { console.warn("Could not parse date from first event."); }
            }
            this.calendarStart = new Date(`${refDateStr}T${this.options.dayStartTime}:00`);
            this.calendarEnd = new Date(`${refDateStr}T${this.options.dayEndTime}:00`);
            if (endH < startH || (endH === startH && endM < startM)) {
                this.calendarEnd.setDate(this.calendarEnd.getDate() + 1);
            }
        } else {
            if (this.options.events.length === 0) {
                this.calendarStart = new Date(); this.calendarStart.setHours(8, 0, 0, 0);
                this.calendarEnd = new Date(); this.calendarEnd.setHours(22, 0, 0, 0);
            } else {
                const eventTimes = this.options.events.flatMap(e => {
                    try { return [new Date(e.startTime), new Date(e.endTime)]; }
                    catch (err) { console.warn(`Invalid date for event ${e.id || e.title}.`); return []; }
                }).filter(date => !isNaN(date));
                if (eventTimes.length === 0) {
                    this.calendarStart = new Date(); this.calendarStart.setHours(8,0,0,0);
                    this.calendarEnd = new Date(); this.calendarEnd.setHours(22,0,0,0);
                } else {
                    this.calendarStart = new Date(Math.min(...eventTimes));
                    this.calendarEnd = new Date(Math.max(...eventTimes));
                }
                this.calendarStart.setMinutes(0, 0, 0);
                if (this.calendarEnd.getMinutes() > 0 || this.calendarEnd.getSeconds() > 0 || this.calendarEnd.getMilliseconds() > 0) {
                    this.calendarEnd.setHours(this.calendarEnd.getHours() + 1, 0, 0, 0);
                }
            }
        }
        if (this.calendarEnd <= this.calendarStart) {
             this.calendarEnd.setHours(this.calendarStart.getHours() + Math.max(1, 24 - this.calendarStart.getHours() + this.calendarEnd.getHours()));
        }
        this.totalHours = Math.max(1, (this.calendarEnd - this.calendarStart) / (1000 * 60 * 60));
    }

    formatTime(date) {
        if (isNaN(date)) return "Invalid Date";
        return date.toLocaleTimeString('da-DK', this.options.timeFormat);
    }

    render() {
        this.container.innerHTML = ''; 
        const calendarEl = document.createElement('div');
        calendarEl.classList.add(
            'festival-calendar', 'flex', 'relative', 'border', 'border-slate-300', 
            'bg-white', 'rounded-lg', 'shadow-lg', 'min-h-svh-600'
        );
        const timeAxisEl = this.renderTimeAxis();
        calendarEl.appendChild(timeAxisEl);
        const scenesWrapperEl = document.createElement('div');
        scenesWrapperEl.classList.add('fc-scenes-wrapper', 'flex', 'flex-grow'); 
        this.options.scenes.forEach((scene, index) => {
            const sceneEl = this.renderScene(scene, index === 0);
            scenesWrapperEl.appendChild(sceneEl);
        });
        calendarEl.appendChild(scenesWrapperEl);
        this.container.appendChild(calendarEl);
        this.options.events.forEach(event => { this.renderEvent(event); });
    }

    renderTimeAxis() {
        // ... (samme som før)
        const timeAxisEl = document.createElement('div');
        timeAxisEl.classList.add(
            'w-12', 'sm:w-16', 
            'border-r', 'border-slate-200', 'pt-10', 
            'sticky', 'left-0', 'bg-slate-50', 'z-20'
        );
        for (let i = 0; i < this.totalHours; i++) {
            const timeSlotEl = document.createElement('div');
            timeSlotEl.classList.add(
                'flex', 'items-center', 'justify-center', 
                'text-[10px]', 'sm:text-xs', 
                'text-slate-600', 'border-b', 'border-dotted', 'border-slate-300', 'box-border'
            );
            if (i === this.totalHours - 1) {
                timeSlotEl.classList.remove('border-b', 'border-dotted', 'border-slate-300');
            }
            const hourTime = new Date(this.calendarStart);
            hourTime.setHours(hourTime.getHours() + i);
            timeSlotEl.textContent = this.formatTime(hourTime);
            timeSlotEl.style.height = `${this.options.pixelsPerHour}px`;
            timeAxisEl.appendChild(timeSlotEl);
        }
        return timeAxisEl;
    }

    renderScene(scene, isFirstScene) {
        // ... (samme som før)
        const sceneEl = document.createElement('div');
        sceneEl.classList.add(
            'fc-scene', 'flex-1', 
            'sm:flex-grow', 'sm:flex-shrink-0', 
            'sm:min-w-[180px]', 'md:min-w-[220px]', 'lg:min-w-[260px]', 
            'relative'
        );
        if (!isFirstScene) {
            sceneEl.classList.add('border-l', 'border-slate-200');
        }
        sceneEl.dataset.sceneId = FestivalCalendar.slugify(scene.name);
        const headerEl = document.createElement('div');
        headerEl.classList.add(
            'h-10', 'flex', 'items-center', 'justify-center', 'text-center',
            'font-semibold', 'text-xs', 'sm:text-sm', 
            'text-slate-700', 'bg-slate-100', 'border-b', 'border-slate-300', 
            'sticky', 'top-0', 'z-30', 'px-1', 'sm:px-2', 'truncate'
        );
        headerEl.textContent = scene.name;
        sceneEl.appendChild(headerEl);
        const bodyEl = document.createElement('div');
        bodyEl.classList.add('relative', 'fc-scene-body-area'); 
        for (let i = 0; i < this.totalHours; i++) {
            const timeSlotLineEl = document.createElement('div');
            timeSlotLineEl.classList.add(
                'border-b', 'border-dotted', 'border-slate-300', 'box-border'
            );
            if (i === this.totalHours - 1) {
                timeSlotLineEl.classList.remove('border-b', 'border-dotted', 'border-slate-300');
            }
            timeSlotLineEl.style.height = `${this.options.pixelsPerHour}px`;
            bodyEl.appendChild(timeSlotLineEl);
        }
        sceneEl.appendChild(bodyEl);
        return sceneEl;
    }

    renderEvent(eventData) {
        const slugifiedSceneId = FestivalCalendar.slugify(eventData.sceneId);
        const sceneSpecificSelector = `.fc-scene[data-scene-id="${slugifiedSceneId}"] .fc-scene-body-area`;
        const sceneBodyEl = this.container.querySelector(sceneSpecificSelector);

        if (!sceneBodyEl) {
            console.warn(`[renderEvent WARN] Scene body for slugifiedId "${slugifiedSceneId}" (original: "${eventData.sceneId}") not found for event "${eventData.title}".`);
            return;
        }

        const eventEl = document.createElement('div');
        eventEl.classList.add(
            'absolute', 'left-[2px]', 'right-[2px]', 'sm:left-[6px]', 'sm:right-[6px]',
            'text-white', 'p-1', 'sm:p-1.5', 'rounded', 'shadow-md', 
            'text-[10px]', 'sm:text-xs', 'overflow-hidden', 
            'transition-all', 'duration-200', 'ease-in-out', 'z-10',
            'cursor-pointer' 
        );
        
        let colorClasses = ['bg-slate-400', 'hover:bg-slate-500']; 
        switch (eventData.riskLevel?.toLowerCase()) {
            case 'high': colorClasses = ['bg-red-500', 'hover:bg-red-600', 'border-red-700']; break;
            case 'medium': colorClasses = ['bg-yellow-400', 'hover:bg-yellow-500', 'text-yellow-800', 'border-yellow-600']; break;
            case 'low': colorClasses = ['bg-green-500', 'hover:bg-green-600', 'border-green-700']; break;
        }
        colorClasses.forEach(cls => eventEl.classList.add(cls));
        eventEl.classList.add('border-b-2', 'sm:border-b-4');

        let startTime, endTime;
        try {
            startTime = new Date(eventData.startTime); 
            if (eventData.endTime === null) {
                endTime = new Date(startTime.getTime() + 60 * 60 * 1000); 
            } else {
                endTime = new Date(eventData.endTime); 
            }
            if (isNaN(startTime) || isNaN(endTime)) throw new Error("Invalid date for event.");
        } catch (e) {
            console.error(`Invalid date for event "${eventData.title || eventData.id}". Skipping.`); return;
        }

        let startOffsetMinutes = (startTime - this.calendarStart) / (1000 * 60);
        let durationMinutes = (endTime - startTime) / (1000 * 60);
        
        const eventActualStart = new Date(Math.max(startTime.getTime(), this.calendarStart.getTime()));
        const eventActualEnd = new Date(Math.min(endTime.getTime(), this.calendarEnd.getTime()));

        if (eventActualEnd.getTime() <= eventActualStart.getTime() || durationMinutes <= 0) { 
            return; 
        }
        
        startOffsetMinutes = (eventActualStart.getTime() - this.calendarStart.getTime()) / (1000 * 60);
        durationMinutes = (eventActualEnd.getTime() - eventActualStart.getTime()) / (1000 * 60);
        
        if (durationMinutes <=0) { 
            return;
        }

        const topPosition = (startOffsetMinutes / 60) * this.options.pixelsPerHour;
        const height = Math.max(18, (durationMinutes / 60) * this.options.pixelsPerHour - 2); 

        eventEl.style.top = `${topPosition}px`;
        eventEl.style.height = `${height}px`;

        const titleEl = document.createElement('div');
        titleEl.classList.add('font-semibold', 'whitespace-nowrap', 'overflow-hidden', 'text-ellipsis');
        titleEl.textContent = eventData.title;
        eventEl.appendChild(titleEl);

        if (height > (window.innerWidth < 640 ? 22 : 25) ) {
            const timeEl = document.createElement('div');
            timeEl.classList.add('text-[9px]', 'sm:text-[10px]', 'opacity-80');
            timeEl.textContent = `${this.formatTime(startTime)} - ${this.formatTime(endTime)}`;
            eventEl.appendChild(timeEl);
        }
        
        if (eventData.description && height > 60 && window.innerWidth >= 640) { 
            const descriptionEl = document.createElement('div');
            descriptionEl.classList.add('text-[10px]', 'mt-1', 'line-clamp-2'); 
            descriptionEl.textContent = eventData.description;
            eventEl.appendChild(descriptionEl);
        }

        eventEl.addEventListener('click', () => {
            this.showModal(eventData);
        });
                
        sceneBodyEl.appendChild(eventEl);
    }
}