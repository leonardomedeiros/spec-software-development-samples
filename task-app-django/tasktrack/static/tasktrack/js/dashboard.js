// Restore scroll position after a page reload triggered by this script (e.g. task deletion)
document.addEventListener('DOMContentLoaded', function() {
    const savedScrollY = sessionStorage.getItem('taskTrackScrollY');
    if (savedScrollY !== null) {
        sessionStorage.removeItem('taskTrackScrollY');
        window.scrollTo(0, parseInt(savedScrollY, 10) || 0);
    }
});

document.addEventListener('DOMContentLoaded', function() {
    // Handle create task form - find the form inside the modalTask
    const modalTask = document.getElementById('modalTask');
    if (modalTask) {
        const createTaskForm = modalTask.querySelector('form[action="/web/tasks"]');
        console.log('Create task form found:', createTaskForm);
        if (createTaskForm) {
            createTaskForm.addEventListener('submit', function(e) {
            e.preventDefault();

            const formData = new FormData(createTaskForm);
            const csrfToken = formData.get('csrfmiddlewaretoken');

            // Build request body as URL-encoded form data
            const params = new URLSearchParams();
            params.append('csrfmiddlewaretoken', csrfToken);
            params.append('project_id', formData.get('project_id'));
            params.append('title', formData.get('title'));
            params.append('description', formData.get('description') || '');
            params.append('priority', formData.get('priority'));
            params.append('assignee_id', formData.get('assignee_id') || '');
            params.append('due_date', formData.get('due_date') || '');

            // Submit using fetch
            fetch(createTaskForm.action, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: params.toString()
            })
            .then(response => {
                if (response.ok) {
                    window.location.reload();
                } else {
                    return response.text().then(text => {
                        const parser = new DOMParser();
                        const doc = parser.parseFromString(text, 'text/html');
                        const errorEl = doc.querySelector('[class*="alert-danger"], [class*="messages"] li');
                        const message = errorEl ? errorEl.textContent.trim() : 'Não foi possível processar a tarefa. Verifique os dados e tente novamente.';
                        alert('⚠️ ' + message);
                    });
                }
            })
            .catch(error => {
                alert('⚠️ Houve um problema ao processar sua solicitação. Tente novamente.');
            });
            });
        }
    }

    // Handle edit task form
    const modalEl = document.getElementById('modalEditTask');
    const formEl = document.getElementById('formEditTask');

    if (modalEl) {
        modalEl.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            if (!button) return;

            const taskId = button.getAttribute('data-task-id');
            const taskTitle = button.getAttribute('data-task-title') || '';
            const taskDesc = button.getAttribute('data-task-description') || '';
            const taskPrio = button.getAttribute('data-task-priority') || '';
            const taskAssignee = button.getAttribute('data-task-assignee') || '';
            const taskDueDateRaw = button.getAttribute('data-task-due-date') || '';
            const taskGithubUrl = button.getAttribute('data-task-github-url') || '';

            // Convert datetime/date string to YYYY-MM-DD format for date input
            let taskDueDate = '';
            if (taskDueDateRaw) {
                // Handle both ISO datetime and date formats
                const dateObj = new Date(taskDueDateRaw);
                if (!isNaN(dateObj.getTime())) {
                    taskDueDate = dateObj.toISOString().split('T')[0];
                }
            }

            document.getElementById('currentTaskId').value = taskId;
            document.getElementById('editTaskTitle').value = taskTitle;
            document.getElementById('editTaskDescription').value = taskDesc;
            document.getElementById('editTaskPriority').value = taskPrio;
            document.getElementById('editTaskAssignee').value = taskAssignee;
            document.getElementById('editTaskDueDate').value = taskDueDate;
            document.getElementById('editTaskGithubUrl').value = taskGithubUrl;

            formEl.action = `/web/tasks/${taskId}`;
        });

        formEl.addEventListener('submit', function(e) {
            e.preventDefault();

            const taskId = document.getElementById('currentTaskId').value;
            const formData = new FormData(formEl);
            const csrfToken = formData.get('csrfmiddlewaretoken');

            // Build request body as URL-encoded form data
            const params = new URLSearchParams();
            params.append('csrfmiddlewaretoken', csrfToken);

            // Add all fields, empty ones will be sent as empty strings
            const title = formData.get('title') || '';
            const description = formData.get('description') || '';
            const priority = formData.get('priority') || '';
            const assigneeId = formData.get('assignee_id') || '';
            const dueDate = formData.get('due_date') || '';
            const githubUrl = formData.get('github_url') || '';

            if (title) params.append('title', title);
            if (description) params.append('description', description);
            if (priority) params.append('priority', priority);
            if (assigneeId) params.append('assignee_id', assigneeId);
            if (dueDate) params.append('due_date', dueDate);
            if (githubUrl) params.append('github_url', githubUrl);

            fetch(formEl.action, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: params.toString()
            })
            .then(response => {
                if (response.ok) {
                    window.location.reload();
                } else {
                    return response.text().then(text => {
                        const parser = new DOMParser();
                        const doc = parser.parseFromString(text, 'text/html');
                        const errorEl = doc.querySelector('[class*="alert-danger"], [class*="messages"] li');
                        const message = errorEl ? errorEl.textContent.trim() : 'Não foi possível atualizar a tarefa. Verifique os dados e tente novamente.';
                        alert('⚠️ ' + message);
                    });
                }
            })
            .catch(error => {
                alert('⚠️ Houve um problema ao processar sua solicitação. Tente novamente.');
            });
        });
    }
});

// Marca (checked = true/false) as checkboxes de um container cujo value esteja na lista de ids fornecida.
// idsAttr é uma string separada por vírgulas (ex: "id1,id2"); containerId é o elemento que envolve os checkboxes.
function _syncCheckboxesFromIds(containerId, idsAttr) {
    const container = document.getElementById(containerId);
    if (!container) return;
    const ids = new Set((idsAttr || '').split(',').map(function (id) { return id.trim(); }).filter(Boolean));
    container.querySelectorAll('input[type="checkbox"]').forEach(function (checkbox) {
        checkbox.checked = ids.has(checkbox.value);
    });
}

// Handle edit requirement modal prefill
document.addEventListener('DOMContentLoaded', function() {
    const modalEditReq = document.getElementById('modalEditRequirement');
    const formEditReq = document.getElementById('formEditRequirement');
    if (modalEditReq && formEditReq) {
        modalEditReq.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            if (!button) return;

            const reqId = button.getAttribute('data-req-id');
            document.getElementById('editReqCode').value = button.getAttribute('data-req-code') || '';
            document.getElementById('editReqTitle').value = button.getAttribute('data-req-title') || '';
            document.getElementById('editReqDescription').value = button.getAttribute('data-req-description') || '';
            document.getElementById('editReqType').value = button.getAttribute('data-req-type') || '';
            document.getElementById('editReqPriority').value = button.getAttribute('data-req-priority') || '';
            _syncCheckboxesFromIds('editReqTasks', button.getAttribute('data-req-task-ids'));
            _syncCheckboxesFromIds('editReqActors', button.getAttribute('data-req-actor-ids'));

            formEditReq.action = `/web/requirements/${reqId}`;
        });
    }
});

// Handle view requirement modal (somente leitura)
document.addEventListener('DOMContentLoaded', function() {
    const modalViewReq = document.getElementById('modalViewRequirement');
    if (modalViewReq) {
        modalViewReq.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            if (!button) return;

            document.getElementById('viewReqCode').value = button.getAttribute('data-req-code') || '';
            document.getElementById('viewReqTitle').value = button.getAttribute('data-req-title') || '';
            document.getElementById('viewReqDescription').value = button.getAttribute('data-req-description') || '';
            document.getElementById('viewReqType').value = button.getAttribute('data-req-type') || '';
            document.getElementById('viewReqPriority').value = button.getAttribute('data-req-priority') || '';
            document.getElementById('viewReqStatus').value = button.getAttribute('data-req-status') || '';

            _syncCheckboxesFromIds('viewReqTasks', button.getAttribute('data-req-task-ids'));
            _syncCheckboxesFromIds('viewReqActors', button.getAttribute('data-req-actor-ids'));
        });
    }
});

// Handle edit contract modal prefill
document.addEventListener('DOMContentLoaded', function() {
    const modalEditContract = document.getElementById('modalEditContract');
    const formEditContract = document.getElementById('formEditContract');
    if (modalEditContract && formEditContract) {
        modalEditContract.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            if (!button) return;

            const contractId = button.getAttribute('data-contract-id');
            document.getElementById('editContractTitle').value = button.getAttribute('data-contract-title') || '';
            document.getElementById('editContractDescription').value = button.getAttribute('data-contract-description') || '';
            document.getElementById('editContractOwner').value = button.getAttribute('data-contract-owner') || '';

            formEditContract.action = `/web/contracts/${contractId}`;
        });
    }
});

// Handle edit project modal prefill
document.addEventListener('DOMContentLoaded', function() {
    const modalEditProject = document.getElementById('modalEditProject');
    const formEditProject = document.getElementById('formEditProject');
    if (modalEditProject && formEditProject) {
        modalEditProject.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            if (!button) return;

            const projectId = button.getAttribute('data-project-id');
            document.getElementById('editProjectTitle').value = button.getAttribute('data-project-title') || '';
            document.getElementById('editProjectDescription').value = button.getAttribute('data-project-description') || '';
            document.getElementById('editProjectOwner').value = button.getAttribute('data-project-owner') || '';

            formEditProject.action = `/web/projects/${projectId}`;
        });
    }
});

// Handle edit actor modal prefill
document.addEventListener('DOMContentLoaded', function() {
    const modalEditActor = document.getElementById('modalEditActor');
    const formEditActor = document.getElementById('formEditActor');
    if (modalEditActor && formEditActor) {
        modalEditActor.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            if (!button) return;

            const actorId = button.getAttribute('data-actor-id');
            document.getElementById('editActorName').value = button.getAttribute('data-actor-name') || '';
            document.getElementById('editActorDescription').value = button.getAttribute('data-actor-description') || '';

            formEditActor.action = `/web/actors/${actorId}`;
        });
    }
});

// Handle delete confirmation modal (tasks, requirements, contracts, projects)
document.addEventListener('click', function(e) {
    if (e.target.closest('form[action*="/delete"]')) {
        const button = e.target.closest('button[type="submit"]');
        if (button && button.closest('form[action*="/delete"]')) {
            e.preventDefault();
            const form = button.closest('form');
            const entityType = form.getAttribute('data-entity-type') || 'tarefa';
            const entityWarning = form.getAttribute('data-entity-warning') || '';

            const warningEl = document.getElementById('confirmDeleteWarning');
            warningEl.textContent = entityWarning;
            warningEl.hidden = !entityWarning;
            document.getElementById('confirmDeleteEntityLabel').textContent = `excluir este(a) ${entityType}`;
            document.getElementById('confirmDeleteBtnLabel').textContent = `Excluir ${entityType.charAt(0).toUpperCase()}${entityType.slice(1)}`;

            // Show confirmation modal
            const modalEl = new bootstrap.Modal(document.getElementById('confirmDeleteModal'));
            document.getElementById('confirmDeleteBtn').onclick = function() {
                modalEl.hide();
                sessionStorage.setItem('taskTrackScrollY', String(window.scrollY));
                form.submit();
            };
            modalEl.show();
        }
    }
});
