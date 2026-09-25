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

    if (modalEl && formEl) {
        document.querySelectorAll('[data-bs-target="#modalEditTask"]').forEach(function(btn) {
            btn.addEventListener('click', function() {
                const taskId = this.getAttribute('data-task-id');
                const taskTitle = this.getAttribute('data-task-title') || '';
                const taskDesc = this.getAttribute('data-task-description') || '';
                const taskPrio = this.getAttribute('data-task-priority') || '';
                const taskAssignee = this.getAttribute('data-task-assignee') || '';
                const taskDueDateRaw = this.getAttribute('data-task-due-date') || '';
                const taskGithubUrl = this.getAttribute('data-task-github-url') || '';

                let taskDueDate = '';
                if (taskDueDateRaw) {
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
    const formEditReq = document.getElementById('formEditRequirement');
    if (formEditReq) {
        document.querySelectorAll('[data-bs-target="#modalEditRequirement"]').forEach(function(btn) {
            btn.addEventListener('click', function() {
                const reqId = this.getAttribute('data-req-id');
                document.getElementById('editReqCode').value = this.getAttribute('data-req-code') || '';
                document.getElementById('editReqTitle').value = this.getAttribute('data-req-title') || '';
                document.getElementById('editReqDescription').value = this.getAttribute('data-req-description') || '';
                document.getElementById('editReqType').value = this.getAttribute('data-req-type') || '';
                document.getElementById('editReqPriority').value = this.getAttribute('data-req-priority') || '';
                _syncCheckboxesFromIds('editReqTasks', this.getAttribute('data-req-task-ids'));
                _syncCheckboxesFromIds('editReqActors', this.getAttribute('data-req-actor-ids'));
                formEditReq.action = `/web/requirements/${reqId}`;
            });
        });
    }
});

// Handle view requirement modal (somente leitura)
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('[data-bs-target="#modalViewRequirement"]').forEach(function(btn) {
        btn.addEventListener('click', function() {
            document.getElementById('viewReqCode').value = this.getAttribute('data-req-code') || '';
            document.getElementById('viewReqTitle').value = this.getAttribute('data-req-title') || '';
            document.getElementById('viewReqDescription').value = this.getAttribute('data-req-description') || '';
            document.getElementById('viewReqType').value = this.getAttribute('data-req-type') || '';
            document.getElementById('viewReqPriority').value = this.getAttribute('data-req-priority') || '';
            document.getElementById('viewReqStatus').value = this.getAttribute('data-req-status') || '';
            _syncCheckboxesFromIds('viewReqTasks', this.getAttribute('data-req-task-ids'));
            _syncCheckboxesFromIds('viewReqActors', this.getAttribute('data-req-actor-ids'));
        });
    });
});

// Handle edit contract modal prefill
document.addEventListener('DOMContentLoaded', function() {
    const formEditContract = document.getElementById('formEditContract');
    if (formEditContract) {
        document.querySelectorAll('[data-bs-target="#modalEditContract"]').forEach(function(btn) {
            btn.addEventListener('click', function() {
                const contractId = this.getAttribute('data-contract-id');
                document.getElementById('editContractTitle').value = this.getAttribute('data-contract-title') || '';
                document.getElementById('editContractDescription').value = this.getAttribute('data-contract-description') || '';
                document.getElementById('editContractOwner').value = this.getAttribute('data-contract-owner') || '';
                formEditContract.action = `/web/contracts/${contractId}`;
            });
        });
    }
});

// Handle edit project modal prefill
document.addEventListener('DOMContentLoaded', function() {
    const formEditProject = document.getElementById('formEditProject');
    if (formEditProject) {
        document.querySelectorAll('[data-bs-target="#modalEditProject"]').forEach(function(btn) {
            btn.addEventListener('click', function() {
                const projectId = this.getAttribute('data-project-id');
                document.getElementById('editProjectTitle').value = this.getAttribute('data-project-title') || '';
                document.getElementById('editProjectDescription').value = this.getAttribute('data-project-description') || '';
                document.getElementById('editProjectOwner').value = this.getAttribute('data-project-owner') || '';
                formEditProject.action = `/web/projects/${projectId}`;
            });
        });
    }
});

// Handle edit actor modal prefill
document.addEventListener('DOMContentLoaded', function() {
    const formEditActor = document.getElementById('formEditActor');
    if (formEditActor) {
        document.querySelectorAll('[data-bs-target="#modalEditActor"]').forEach(function(btn) {
            btn.addEventListener('click', function() {
                const actorId = this.getAttribute('data-actor-id');
                document.getElementById('editActorName').value = this.getAttribute('data-actor-name') || '';
                document.getElementById('editActorDescription').value = this.getAttribute('data-actor-description') || '';
                formEditActor.action = `/web/actors/${actorId}`;
            });
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
