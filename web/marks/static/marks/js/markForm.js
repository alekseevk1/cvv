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

// function encodeData(s) {
//     return encodeURIComponent(s).replace(/\-/g, "%2D").replace(/\_/g, "%5F").replace(/\./g, "%2E").replace(/\!/g, "%21").replace(/\~/g, "%7E").replace(/\*/g, "%2A").replace(/\'/g, "%27").replace(/\(/g, "%28").replace(/\)/g, "%29");
// }

function collect_attrs_data() {
    var attrs = [];
    $("input[id^='attr_checkbox__']").each(function () {
        var attr_name = $(this).val().replace(/^attr_checkbox__/,"");
        attrs.push({
            attr: $(this).val(),
            is_compare: $(this).is(':checked'),
            value: $("[id='attr_values__" + attr_name + "']").val(),
            op: $("[id='attr_op__" + attr_name + "']").val()
        });
    });
    return attrs;
}

function get_description() {
    var tmp_div = $('<div>').html($('#mark_description').val());
    tmp_div.find('script').remove();
    tmp_div.find('*').each(function () {
        var element_in_div = $(this);
        $.each($(this)[0].attributes, function (i, attr) { if (attr.name.match("^on")) element_in_div.removeAttr(attr.name) });
    });
    return tmp_div.html();
}

function is_modifiable() {
    var is_modifiable_checkbox = $('#is_modifiable');
    if (is_modifiable_checkbox.length) {
        return is_modifiable_checkbox.is(':checked');
    }
    return true;
}

function collect_markdata() {
    var action = $('#action').val(), obj_type = $('#obj_type').val(), mark_data = {
        description: get_description(), is_modifiable: is_modifiable(), attrs: collect_attrs_data(),
        status: $("input[name='selected_status']:checked").val(),
        comment: $('#mark_comment').val()
    };
    if (action === 'edit') {
        mark_data['autoconfirm'] = $('#autoconfirm').is(':checked');
    }

    if (obj_type === 'unknown') {
        mark_data['problem'] = $('#unknown_problem_pattern').val();
        mark_data['function'] = $('#unknown_function').val();
        mark_data['is_regexp'] = $('#is_regexp').is(':checked');
        mark_data['link'] = $('#unknown_link').val();
    }
    else {
        mark_data['verdict'] = $("input[name='selected_verdict']:checked").val();
        mark_data['tags'] = get_tags_values();
        if (obj_type === 'unsafe') mark_data['compare_id'] = $("#compare_function").val();
    }
    if (obj_type === 'unsafe') {
        mark_data['edited_error_trace'] = $('#converted_error_trace').val();
        mark_data['conversion_function'] = JSON.parse($('#conversion_function').val().replace(/\'/g, '"')).name;
        mark_data['comparison_function'] = JSON.parse($('#comparison_function').val().replace(/\'/g, '"')).name;
        mark_data['similarity_threshold'] = $('#similarity_threshold').val();
        mark_data['initial_error_trace'] = $('#report_id').val();
        mark_data['conversion_function_args'] = get_conversion_function_args();
        mark_data['apply_for_current'] = $('#apply_for_current').is(':checked');
        mark_data['do_not_recalc'] = $('#do_not_recalc').is(':checked');
    }
    mark_data['report_to_redirect'] = $('#report_to_redirect').val();
    return JSON.stringify(mark_data);
}

function set_action_on_func_change() {
    $.post('/marks/get_func_description/' + $(this).children('option:selected').val() + '/', {}, function (data) {
        if (data.error) {
            err_notify(data.error);
            return false;
        }
        $('#compare_function_description').text(data['compare_desc']);
        $('#convert_function_description').text(data['convert_desc']);
        $('#convert_function_name').text(data['convert_name']);
    });
}

function get_conversion_function() {
    return JSON.parse($('#conversion_function').val().replace(/\'/g, '"')).name;
}

function get_conversion_function_args() {
    var args = {};
    var conversion_function = get_conversion_function();
    args['additional_model_functions'] = $('#additional_model_functions').val();
    args['filtered_model_functions'] = $('#filtered_model_functions').val();
    args['use_notes'] = $('#model_functions_use_notes').is(':checked');
    args['ignore_notes_text'] = $('#model_functions_ignore_notes_text').is(':checked');
    args['use_warns'] = $('#model_functions_use_warns').is(':checked');
    return JSON.stringify(args);
}

function update_converted_error_trace(conversion_function) {
    $.post(
        '/marks/get_converted_trace/' + $('#report_id').val() +'/',
        {
            "conversion": conversion_function,
            "args": get_conversion_function_args()
        },
        function (data) {
            if (data.error) {
                err_notify(data.error);
                return false;
            }
            $('#converted_error_trace').val(data['converted_error_trace']);
        }
    );
}


function conversion_function_change(new_function) {
    obj = JSON.parse(new_function.replace(/\'/g, '"'));
    $('#conversion_function_description').text(obj.desc);
    if (obj.name != 'model functions' && obj.name != 'model functions with notes') {
        $('#additional_model_functions').hide();
    } else {
        $('#additional_model_functions').val(null);
        $('#additional_model_functions').show();
    }
    if (obj.name != 'model functions' && obj.name != 'model functions with notes' &&  obj.name != 'call tree' &&
        obj.name != 'full')  {
        $('#filtered_model_functions').hide();
    } else {
        $('#filtered_model_functions').val(null);
        $('#filtered_model_functions').show();
    }
    update_converted_error_trace(obj.name);
}

function update_converted_error_trace_on_args(args) {
    update_converted_error_trace(get_conversion_function());
}


function change_initial_error_trace(report_id) {
    $('#report_id').val(report_id);
    update_converted_error_trace(get_conversion_function());
}

function comparison_function_change(new_function) {
    obj = JSON.parse(new_function.replace(/\'/g, '"'));
    $('#comparison_function_description').text(obj.desc);
}

function test_unknown_function() {
    var func = $('#unknown_function').val();
    if (func.length <= 0) {
        err_notify($('#error__function_required').text());
        return false;
    }
    $.post(
        '/marks/check-unknown-mark/' + $('#obj_id').val() + '/',
        {
            function: func,
            pattern: $('#unknown_problem_pattern').val(),
            is_regex: $('#is_regexp').is(':checked')
        },
        function (data) {
            if (data.error) {
                err_notify(data.error);
                $('#test_mark_nomatch_div').hide();
                $('#test_mark_result_div').hide();
            }
            else {
                if (data['matched'] === 1) {
                    $('#test_mark_nomatch_div').hide();
                    $('#test_mark_problem').text(data['problem']);
                    $('#test_mark_result').text(data['result']);
                    $('#test_mark_result_div').show();
                }
                else {
                    $('#test_mark_result_div').hide();
                    $('#test_mark_nomatch_div').show();
                    if (data['result'].length > 0) {
                        $('#regexp_err_result').text(data['result']).show();
                    }
                    else {
                        $('#regexp_err_result').text('').hide();
                    }
                }
            }
        }
    );
}

function save_mark() {
    $('#progress_bar_popup').modal('show');
    var mark_id = 0;
    var update_progress_interval = null;
    var time_start = performance.now();
    if ($('#action').val() == 'edit') {
        mark_id = $('#obj_id').val();
    }
    update_progress_interval = setInterval(function() {mark_id = update_progress(mark_id, time_start);}, 1000);

    $(this).addClass('disabled');
    $.post('', {data: collect_markdata()}, function (data) {
        if (data.error) {
            $('#save_mark_btn').removeClass('disabled');
            $('#progress_bar_popup').modal('hide');
            $('#progress_bar_popup').modal('hide');
            clearInterval(update_progress_interval);
            err_notify(data.error);
        }
        else if ('cache_id' in data) {
            var overall_time = (performance.now() - time_start) / 1000;
            window.location.replace('/marks/' + $('#obj_type').val() + '/association_changes/' + data['cache_id']
                + '/?time=' + overall_time + "&report_to_redirect=" + data['report_to_redirect']);
        }
    });
}

function change_attr_checkbox(attr_name) {
    var values_field = "[id='attr_values__" + attr_name + "']";
    var checkbox_field = "[id='attr_checkbox__" + attr_name + "']";
    if ($(checkbox_field).is(':checked')) {
        $(values_field).removeClass('disabled');
    } else {
        $(values_field).addClass('disabled');
    }
}

$(document).ready(function () {
    activate_tags();
    $('#progress_bar_popup').modal('setting', 'closable', false);
    $('.ui.dropdown').each(function () { if (!$(this).hasClass('search')) $(this).dropdown() });
    $('#compare_function').change(set_action_on_func_change);
    $('#test_unknown_mark').click(test_unknown_function);
    $('#save_mark_btn').click(save_mark);
    $('#mark_version_selector').change(function () {
        window.location.replace(get_url_with_get_parameter(window.location.href, 'version', $(this).val()));
    });
});