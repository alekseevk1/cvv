/*
 * CVV is a continuous verification visualizer.
 * Copyright (c) 2023 ISP RAS (http://www.ispras.ru)
 * Ivannikov Institute for System Programming of the Russian Academy of Sciences
 *
 * Copyright (c) 2018 ISP RAS (http://www.ispras.ru)
 * Ivannikov Institute for System Programming of the Russian Academy of Sciences
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * ee the License for the specific language governing permissions and
 * limitations under the License.
 */

function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = $.trim(cookies[i]);
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function change_view(view_type) {
    $.ajax({
        method: 'post',
        url: '/users/ajax/get_view/',
        dataType: 'json',
        data: {
            view_id: $('#view_list__' + view_type).children('option:selected').val(),
            view_type: view_type
        },
        success: function(data) {
            if (data.error) {
                err_notify(data.error);
            } else {
                var selected_column = $('#view_' + view_type + '__columns').children();
                var available_column = $('#view_available_columns_' + view_type).children();
                var all_columns = {};
                for (var i = 0; i < selected_column.length; i++) {
                    all_columns[selected_column[i].value] = selected_column[i].text;
                }
                selected_column.remove();
                for (var i = 0; i < available_column.length; i++) {
                    all_columns[available_column[i].value] = available_column[i].text;
                }
                available_column.remove();
                for (var i = 0; i < data.columns.length; i++) {
                    var column = data.columns[i];
                    var column_text = column;
                    if (column in all_columns) {
                        column_text = all_columns[column];
                        delete all_columns[column];
                    }
                    $('<option>', {
                        value: column,
                        text: column_text,
                        title: column_text
                    }).appendTo('#view_' + view_type + '__columns');
                }
                for (var key in all_columns){
                    $('<option>', {
                        value: key,
                        text: all_columns[key],
                        title: all_columns[key]
                    }).appendTo('#view_available_columns_' + view_type);
                }
            }
        }
    });
}

function csrfSafeMethod(method) {
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method))
}

$(document).on('change', '.btn-file :file', function () {
    var input = $(this),
        numFiles = input.get(0).files ? input.get(0).files.length : 1,
        label = input.val().replace(/\\/g, '/').replace(/.*\//, '');
    input.trigger('fileselect', [numFiles, label]);
});

$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
            var csrftoken = getCookie('csrftoken');
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
    }
});
$(document).ajaxError(function () {
    err_notify($('#error__ajax_error').text());
});

$.extend({
    redirectPost: function (location, args) {
        var form = '<input type="hidden" name="csrfmiddlewaretoken" value="' + getCookie('csrftoken') + '">';
        $.each(args, function (key, value) {
            form += '<input type="hidden" name="' + key + '" value=\'' + value + '\'>';
        });
        $('<form action="' + location + '" method="POST">' + form + '</form>').appendTo($(document.body)).submit();
    }
});

jQuery.expr[':'].regex = function(elem, index, match) {
    var matchParams = match[3].split(','),
        validLabels = /^(data|css):/,
        attr = {
            method: matchParams[0].match(validLabels) ?
                        matchParams[0].split(':')[0] : 'attr',
            property: matchParams.shift().replace(validLabels,'')
        },
        regexFlags = 'ig',
        regex = new RegExp(matchParams.join('').replace(/^s+|s+$/g,''), regexFlags);
    return regex.test(jQuery(elem)[attr.method](attr.property));
};

window.err_notify = function (message, duration) {
    var notify_opts = {autoHide: false, style: 'bootstrap', className: 'error'};
    if (!isNaN(duration)) {
        notify_opts['autoHide'] = true;
        notify_opts['autoHideDelay'] = duration;
    }
    $.notify(message, notify_opts);
};

window.success_notify = function (message) {
    $.notify(message, {
        autoHide: true,
        autoHideDelay: 2500,
        style: 'bootstrap',
        className: 'success'
    });
};

window.isASCII = function (str) {
    return /^[\x00-\x7F]*$/.test(str);
};

window.encodeQueryData = function(data) {
    return Object.keys(data).map(function(key) {
        return [key, data[key]].map(encodeURIComponent).join("=");
    }).join("&");
};

window.collect_view_data = function(view_type) {
    var data = {};
    $('input[id^="view_data_' + view_type + '__"]').each(function () {
        var data_name = $(this).attr('id').replace('view_data_' + view_type + '__', ''), data_type = $(this).val();

        if (data_type === 'checkboxes') {
            data[data_name] = [];
            $('input[id^="view_' + view_type + '__' + data_name + '__"]').each(function () {
                if ($(this).is(':checked')) {
                    data[data_name].push($(this).attr('id').replace('view_' + view_type + '__' + data_name + '__', ''));
                }
            });
        }
        else if (data_type === 'list') {
            data[data_name] = [];
            $.each($(this).data('list').split('__'), function (i, val) {
                if (val.startsWith('radio_')) {
                    data[data_name].push($('input[name="view_' + view_type + '__' + val + '"]:checked').val());
                }
                else {
                    var element_value = $('#view_' + view_type + '__' + val).val();
                    if (!element_value.length) {
                        delete data[data_name];
                        return false;
                    }
                    data[data_name].push(element_value);
                }
            });
        }
        else if (data_type === 'list_null') {
            data[data_name] = [];
            $.each($(this).data('list').split('__'), function (i, val) {
                if (val.startsWith('radio_')) {
                    data[data_name].push($('input[name="view_' + view_type + '__' + val + '"]:checked').val());
                }
                else {
                    data[data_name].push($('#view_' + view_type + '__' + val).val());
                }
            });
        }
        else if (data_type.startsWith('checkboxes_if_')) {
            if ($('#view_condition_' + view_type + '__' + data_type.replace('checkboxes_if_', '')).is(':checked')) {
                data[data_name] = [];
                $('input[id^="view_' + view_type + '__' + data_name + '__"]').each(function () {
                    if ($(this).is(':checked')) {
                        data[data_name].push($(this).attr('id').replace('view_' + view_type + '__' + data_name + '__', ''));
                    }
                });
            }
        }
        else if (data_type.startsWith('list_if_')) {
            var condition = data_type.replace('list_if_', '');
            if ($('#view_condition_' + view_type + '__' + condition).is(':checked')) {
               data[data_name] = [];
                $.each($(this).data('list').split('__'), function (i, val) {
                    if (val.startsWith('radio_')) {
                        data[data_name].push($('input[name="view_' + view_type + '__' + val + '"]:checked').val());
                    }
                    else {
                        var element_value = $('#view_' + view_type + '__' + val).val();
                        if (!element_value.length) {
                            delete data[data_name];
                            return false;
                        }
                        data[data_name].push(element_value);
                    }
                });
            }
        }
        else if (data_type === 'multiselect') {
            data[data_name] = [];
            $('#view_' + view_type + '__' + data_name).children('option').each(function () {
                data[data_name].push($(this).val());
            });
        }
    });
    return {view: JSON.stringify(data), view_type: view_type};
};

window.set_actions_for_views = function(view_type) {
    var get_params_to_delete = ['page', 'view', 'view_id', 'view_type'];

    $('#view_show_unsaved_btn__' + view_type).click(function () {
        var current_url = window.location.href;
        $.each(get_params_to_delete, function (i, get_param) {
            var re = new RegExp('(' + get_param + '=).*?(&|$)');
            if (current_url.indexOf(get_param + "=") > -1) {
                current_url = current_url.replace(re, '');
            }
        });
        if (current_url.indexOf('?') > -1) {
            if (current_url.slice(-1) !== '&') {
                current_url = current_url + '&';
            }
            current_url = current_url + encodeQueryData(collect_view_data(view_type));
        }
        else {
            current_url = current_url + '?' + encodeQueryData(collect_view_data(view_type));
        }
        window.location.href = current_url;
    });

    $('#view_save_btn__' + view_type).click(function () {
        var view_title = $('#view_name_input__' + view_type).val();
        $.ajax({
            method: 'post',
            url: '/users/ajax/check_view_name/',
            dataType: 'json',
            data: {
                view_title: view_title,
                view_type: view_type
            },
            success: function(data) {
                if (data.error) {
                    err_notify(data.error);
                }
                else {
                    var request_data = collect_view_data(view_type);
                    request_data['title'] = view_title;
                    request_data['view_type'] = view_type;
                    $.ajax({
                        method: 'post',
                        url: '/users/ajax/save_view/',
                        dataType: 'json',
                        data: request_data,
                        success: function(save_data) {
                            if (save_data.error) {
                                err_notify(data.error);
                            }
                            else {
                                $('#view_list__' + view_type).append($('<option>', {
                                    text: save_data['view_name'],
                                    value: save_data['view_id']
                                }));
                                $('#view_name_input__' + view_type).val('');
                                success_notify(save_data.message);
                            }
                        }
                    });
                }
            }
        });
    });

    $('#view_update_btn__' + view_type).click(function () {
        var request_data = collect_view_data(view_type);
        request_data['view_id'] = $('#view_list__' + view_type).children('option:selected').val();
        request_data['view_type'] = view_type;
        $.ajax({
            method: 'post',
            url: '/users/ajax/save_view/',
            dataType: 'json',
            data: request_data,
            success: function(save_data) {
                save_data.error ? err_notify(save_data.error) : success_notify(save_data.message);
            }
        });
    });

    $('#view_show_btn__' + view_type).click(function () {
        var current_url = window.location.href, get_data = {
            view_id: $('#view_list__' + view_type).children('option:selected').val(),
            view_type: view_type
        };
        $.each(get_params_to_delete, function (i, get_param) {
            var re = new RegExp('(' + get_param + '=).*?(&|$)');
            if (current_url.indexOf(get_param + "=") > -1) {
                current_url = current_url.replace(re, '');
            }
        });
        if (current_url.indexOf('?') > -1) {
            if (current_url.slice(-1) !== '&') {
                current_url = current_url + '&';
            }
            current_url = current_url + encodeQueryData(get_data);
        }
        else {
            current_url = current_url + '?' + encodeQueryData(get_data);
        }
        window.location.href = current_url;
    });

    $('#view_remove_btn__' + view_type).click(function () {
        $.ajax({
            method: 'post',
            url: '/users/ajax/remove_view/',
            dataType: 'json',
            data: {
                view_id: $('#view_list__' + view_type).children('option:selected').val(),
                view_type: view_type
            },
            success: function(data) {
                if (data.error) {
                    err_notify(data.error)
                }
                else {
                    $('#view_list__' + view_type).children('option:selected').remove();
                    success_notify(data.message)
                }
            }
        });
    });
    $('#view_share_btn__' + view_type).click(function () {
        $.ajax({
            method: 'post',
            url: '/users/ajax/share_view/',
            dataType: 'json',
            data: {
                view_id: $('#view_list__' + view_type).children('option:selected').val(),
                view_type: view_type
            },
            success: function(data) {
                if (data.error) {
                    err_notify(data.error)
                }
                else {
                    success_notify(data.message)
                }
            }
        });
    });

    $('#view_prefer_btn__' + view_type).click(function () {
        $.ajax({
            method: 'post',
            url: '/users/ajax/preferable_view/',
            dataType: 'json',
            data: {
                view_id: $('#view_list__' + view_type).children('option:selected').val(),
                view_type: view_type
            },
            success: function(data) {
                data.error ? err_notify(data.error) : success_notify(data.message);
            }
        });
    });

    $('#view_show_default_btn__' + view_type).click(function () {
        var current_url = window.location.href;
        $.each(get_params_to_delete, function (i, get_param) {
            var re = new RegExp('(' + get_param + '=).*?(&|$)');
            if (current_url.indexOf(get_param + "=") > -1) {
                current_url = current_url.replace(re, '');
            }
        });
        if (current_url.slice(-1) === '&') {
            current_url = current_url.substring(0, current_url.length - 1);
        }
        if (current_url.slice(-1) === '?') {
            current_url = current_url.substring(0, current_url.length - 1);
        }
        window.location.href = current_url;
    });

    var show_viewform_btn = $('#view_show_form_btn_' + view_type);
    show_viewform_btn.popup();
    show_viewform_btn.click(function () {
        show_viewform_btn.popup('hide');
        var view_segment = $('#view_form_segment_' + view_type);
        view_segment.is(':visible') ? view_segment.hide() : view_segment.show();
        return false;
    });

    $('#view_add_column_btn_' + view_type).click(function () {
        var selected_column = $('#view_available_columns_' + view_type).children('option:selected');
        for (var i = 0; i < selected_column.length; i++) {
            $('<option>', {
                value: selected_column[i].value,
                text: selected_column[i].text,
                title: selected_column[i].text
            }).appendTo('#view_' + view_type + '__columns');
        }
        selected_column.remove();
        return false;
    });

    $('#view_remove_column_btn_' + view_type).click(function () {
        var selected_column = $('#view_' + view_type + '__columns').children('option:selected');
        for (var i = 0; i < selected_column.length; i++) {
            $('<option>', {
                value: selected_column[i].value,
                text: selected_column[i].text,
                title: selected_column[i].text
            }).appendTo('#view_available_columns_' + view_type);
        }
        selected_column.remove();
        return false;
    });

    $('#view_move_columns_up_' + view_type).click(function () {
        var $op = $('#view_' + view_type + '__columns').children('option:selected');
        if ($op.length) {
            $op.first().prev().before($op);
        }
    });

    $('#view_move_columns_down_' + view_type).click(function () {
        var $op = $('#view_' + view_type + '__columns').children('option:selected');
        if ($op.length) {
            $op.last().next().after($op);
        }
    });

    $('#order_by_attr__' + view_type).parent().checkbox({
        onChecked: function() {$('#order_attr_value_div__' + view_type).show()}
    });
    $('[id^="order_by_"]').each(function () {
        if ($(this).attr('id').startsWith('order_by_attr__') || $(this).attr('id').split('__')[1] !== view_type) {
            return true;
        }
        $(this).parent().checkbox({
            onChecked: function() {
                $('#order_attr_value_div__' + view_type).hide();
            }
        });
    });
};

window.update_colors = function (table) {
    if (!table.hasClass('alternate-color')) {
        return false;
    }
    var is_dark = false;
    table.find('tbody').first().find('tr:visible').each(function () {
        if (is_dark) {
            $(this).css('background', '#f0fcfe');
            is_dark = false;
        }
        else {
            $(this).css('background', 'white');
            is_dark = true;
        }
    });
};

window.getFileExtension = function(name) {
    var found = name.lastIndexOf('.') + 1;
    return found > 0 ? name.substr(found) : "";
};

window.isFileReadable = function(name) {
    var readable_extensions = ['txt', 'json', 'xml', 'c', 'aspect', 'i', 'h', 'tmpl', 'python'],
        extension = getFileExtension(name);
    return ($.inArray(extension, readable_extensions) !== -1 || name == 'README');
};

window.get_url_with_get_parameter = function (url, key, value) {
    if (url.indexOf(key + '=') > -1) {
        var url_regex = new RegExp('(' + key + "=).*?(&|$)");
        return url.replace(url_regex, '$1' + value + '$2');
    }
    else if (url.indexOf('?') > -1) {
        return url + '&' + key + '=' + value;
    }
    else {
        return url + '?' + key + '=' + value;
    }
};

$(document).ready(function () {
    $('.browse').popup({
        inline: true,
        hoverable: true,
        position: 'bottom left',
        delay: {
            show: 300,
            hide: 600
        }
    });
    $('.ui.checkbox').checkbox();
    $('.ui.accordion').accordion();
    $('.note-popup').each(function () {
        var position = $(this).data('position');
        if (position) {
            $(this).popup({position: position});
        }
        else {
            $(this).popup();
        }
    });
    $('.sort-table').each(function () {
        var classes = $(this).attr("class");
        var length = 50;
        var scroll_y = "75vh";
        if (classes.includes('show-all')) {
            length = -1;
        } else if (classes.includes('show-min')) {
            length = 10;
            scroll_y = "45vh";
        }
        var t = $(this).DataTable({
            paging: true,
            lengthMenu: [ [10, 50, 100, 500, -1], [10, 50, 100, 500, $('#trans__sort_all').text()] ],
            pageLength: length,
            orderMulti: true,
            columnDefs: [{
                orderable: false,
                searchable: false,
                targets: 0
            }],
            order: [],
            language: {
                "lengthMenu": $('#trans__sort_length_menu').text(),
                "info":       $('#trans__sort_info').text(),
                "infoEmpty":      $('#trans__sort_info_empty').text(),
                "infoFiltered":   $('#trans__sort_info_filtered').text(),
                "search":         $('#trans__sort_search').text(),
                "zeroRecords":    $('#trans__sort_info_empty').text(),
                "paginate": {
                    "next":       $('#trans__sort_next').text(),
                    "previous":   $('#trans__sort_previous').text()
                },
            },
            scrollCollapse: true,
            "scrollX": true,
            "scrollY": scroll_y
        });
        $(this).addClass("display");
        if (!classes.includes('no-index')) {
            t.on( 'order.dt search.dt', function () {
                t.column(0, {search:'applied', order:'applied'}).nodes().each( function (cell, i) {
                    cell.innerHTML = i+1;
                } );
            } ).draw();
        }
    });

    $('.page-link-icon').click(function () {
        window.location.replace(get_url_with_get_parameter(window.location.href, 'page', $(this).data('page-number')));
    });

    $('.view-type-buttons').each(function () {
        set_actions_for_views($(this).val());
        return true;
    });

    var upload_btn = $('#show_upload_job_popup');
    if (upload_btn.length && !upload_btn.hasClass('disabled')) {
        $('#upload_job_popup').modal({transition: 'vertical flip', onShow: function () {
            var parent_identifier = $('#job_identifier');
            if (parent_identifier.length) {
                $('#upload_job_parent_id').val(parent_identifier.val());
            }
        }}).modal('attach events', '#show_upload_job_popup', 'show');
    }

    var upload_tree_btn = $('#show_upload_jobtree_popup');
    if (upload_tree_btn.length && !upload_tree_btn.hasClass('disabled')) {
        $('#upload_jobtree_popup').modal({transition: 'vertical flip', onShow: function () {
            var parent_identifier = $('#job_identifier');
            if (parent_identifier.length) {
                $('#upload_jobtree_parent_id').val(parent_identifier.val());
            }
        }}).modal('attach events', '#show_upload_jobtree_popup', 'show');
    }

    $('#upload_job_file_input').on('fileselect', function () {
        var files = $(this)[0].files,
            filename_list = $('<ul>');
        for (var i = 0; i < files.length; i++) {
            filename_list.append($('<li>', {text: files[i].name}));
        }
        $('#upload_job_filename').html(filename_list);
    });

    $('#upload_job_cancel').click(function () {
        var file_input = $('#upload_job_file_input');
        file_input.replaceWith(file_input.clone( true ));
        $('#upload_job_parent_id').val('');
        $('#upload_job_filename').empty();
        $('#upload_job_popup').modal('hide');
    });

    $('#upload_jobs_start').click(function () {
        var parent_id = $('#upload_job_parent_id').val(),
            files = $('#upload_job_file_input')[0].files,
            data = new FormData();
        if (parent_id.length === 0) parent_id = 'null';
        if (files.length <= 0) {
            err_notify($('#error__no_file_chosen').text());
            return false;
        }
        for (var i = 0; i < files.length; i++) {
            data.append('file', files[i]);
        }
        $('#upload_job_popup').modal('hide');
        $('#dimmer_of_page').addClass('active');
        $.ajax({
            url: '/jobs/upload_jobs/' + encodeURIComponent(parent_id) + '/',
            type: 'POST',
            data: data,
            dataType: 'json',
            contentType: false,
            processData: false,
            mimeType: 'multipart/form-data',
            xhr: function() {
                return $.ajaxSettings.xhr();
            },
            success: function (data) {
                $('#dimmer_of_page').removeClass('active');
                if ('error' in data) {
                    err_notify(data['error']);
                }
                else {
                    window.location.replace('');
                }
            }
        });
        return false;
    });

    $('#upload_jobtree_file_input').on('fileselect', function () {
        var files = $(this)[0].files,
            filename_list = $('<ul>');
        for (var i = 0; i < files.length; i++) {
            filename_list.append($('<li>', {text: files[i].name}));
        }
        $('#upload_jobtree_filename').html(filename_list);
    });

    $('#upload_jobstree_cancel').click(function () {
        var file_input = $('#upload_jobtree_file_input');
        file_input.replaceWith(file_input.clone( true ));
        $('#upload_jobtree_parent_id').val('');
        $('#upload_jobtree_filename').empty();
        $('#upload_jobtree_popup').modal('hide');
    });

    $('#upload_jobstree_start').click(function () {
        var parent_id = $('#upload_jobtree_parent_id').val();
        if (!parent_id.length) {
            parent_id = '';
        }
        var files = $('#upload_jobtree_file_input')[0].files, data = new FormData();
        if (files.length <= 0) {
            err_notify($('#error__no_file_chosen').text());
            return false;
        }
        data.append('file', files[0]);
        data.append('parent_id', parent_id);
        $('#upload_jobtree_popup').modal('hide');
        $('#dimmer_of_page').addClass('active');
        $.ajax({
            url: '/jobs/upload_jobs_tree/',
            type: 'POST',
            data: data,
            dataType: 'json',
            contentType: false,
            processData: false,
            mimeType: 'multipart/form-data',
            xhr: function() {
                return $.ajaxSettings.xhr();
            },
            success: function (data) {
                $('#dimmer_of_page').removeClass('active');
                if ('error' in data) {
                    err_notify(data['error']);
                }
                else {
                    window.location.replace('');
                }
            }
        });
        return false;
    });

    $('.tag-description-popup').each(function () {
        $(this).popup({
            html: $(this).attr('data-content'),
            hoverable: true
        });
    });
    $('.alternate-color').each(function () {
        update_colors($(this));
    });
});

function switch_report_tags(identifier, report_type) {
    target_id = "detailed_" + report_type + "_tags_" + identifier
    icon_id = "icon_" + report_type + "_tags_" + identifier
    tags_element = document.getElementById(target_id);
    icon_element = document.getElementById(icon_id);
    if (!tags_element) {
        return;
    }
    if (tags_element.hidden) {
        tags_element.hidden = false;
        icon_element.className = "minus circle icon";
    } else {
        tags_element.hidden = true;
        icon_element.className = "plus circle icon";
    }
}
