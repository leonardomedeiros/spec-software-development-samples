// Restore scroll position after a page reload
document.addEventListener('DOMContentLoaded', function() {
    var saved = sessionStorage.getItem('taskTrackScrollY');
    if (saved !== null) {
        sessionStorage.removeItem('taskTrackScrollY');
        window.scrollTo(0, parseInt(saved, 10) || 0);
    }
});

// Create task (modal form)
(function() {
    var modal = document.getElementById('modalTask');
    if (!modal) return;
    var form = modal.querySelector('form[action="/web/tasks"]');
    if (!form) return;
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        var fd = new FormData(form);
        var params = new URLSearchParams();
        params.append('csrfmiddlewaretoken', fd.get('csrfmiddlewaretoken'));
        params.append('project_id', fd.get('project_id'));
        params.append('title', fd.get('title'));
        params.append('description', fd.get('description') || '');
        params.append('priority', fd.get('priority'));
        params.append('assignee_id', fd.get('assignee_id') || '');
        params.append('due_date', fd.get('due_date') || '');
        fetch(form.action, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: params.toString()
        }).then(function(r) {
            if (r.ok) return window.location.reload();
            r.text().then(function(t) {
                var doc = new DOMParser().parseFromString(t, 'text/html');
                var err = doc.querySelector('[class*="alert-danger"], [class*="messages"] li');
                alert(err ? err.textContent.trim() : 'Erro ao criar tarefa.');
            });
        }).catch(function() { alert('Erro de rede. Tente novamente.'); });
    });
})();

// Delete confirmation
document.addEventListener('click', function(e) {
    var button = e.target.closest('button[type="submit"]');
    if (!button) return;
    var form = button.closest('form[action*="/delete"]');
    if (!form) return;
    e.preventDefault();
    var entityType = form.getAttribute('data-entity-type') || 'tarefa';
    var entityWarning = form.getAttribute('data-entity-warning') || '';
    var warningEl = document.getElementById('confirmDeleteWarning');
    warningEl.textContent = entityWarning;
    warningEl.hidden = !entityWarning;
    document.getElementById('confirmDeleteEntityLabel').textContent = 'excluir este(a) ' + entityType;
    document.getElementById('confirmDeleteBtnLabel').textContent = 'Excluir ' + entityType.charAt(0).toUpperCase() + entityType.slice(1);
    var modal = new bootstrap.Modal(document.getElementById('confirmDeleteModal'));
    document.getElementById('confirmDeleteBtn').onclick = function() {
        modal.hide();
        sessionStorage.setItem('taskTrackScrollY', String(window.scrollY));
        form.submit();
    };
    modal.show();
});
