document.addEventListener('DOMContentLoaded', function() {
    const noteForm = document.getElementById('note-form');
    const notesContainer = document.getElementById('notes-container');

    noteForm.addEventListener('submit', function(event) {
        event.preventDefault();

        const formData = new FormData(noteForm);
        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/create_note', true);
        xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');

        xhr.onreadystatechange = function() {
            if (xhr.readyState === XMLHttpRequest.DONE) {
                if (xhr.status === 200) {
                    const response = JSON.parse(xhr.responseText);
                    if (response.success) {
                        addNoteToDOM(response.note);
                        noteForm.reset();
                    } else {
                        alert('Error creating note');
                    }
                }
            }
        };

        xhr.send(formData);
    });

    function addNoteToDOM(note) {
        const noteDiv = document.createElement('div');
        noteDiv.classList.add('note');
        noteDiv.style.backgroundColor = note.color;
        noteDiv.innerHTML = `<p>${note.content}</p>`;
        notesContainer.appendChild(noteDiv);
    }
});
