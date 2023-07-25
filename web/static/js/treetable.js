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

window.inittree = function(table, column, expanded, collapsed) {

    String.prototype.startsWith = function(prefix) {
        return this.indexOf(prefix) === 0;
    };

    function get_ids(tr_class) {
        if (!tr_class) {
            return [null, null, false, false, false];
        }
        var classlist = tr_class.split(/\s+/), tt_par_id = null, tt_id = null, has_children = false,
            has_double_children = false, is_black_list = false;
        $.each(classlist, function(i, item) {
            if (item.startsWith('treegrid-parent-')) {
                tt_par_id = item.replace('treegrid-parent-', '');
            }
            else if (item.startsWith('treegrid-')) {
                tt_id = item.replace('treegrid-', '');
            } else if (item == 'children') {
                has_children = true;
            } else if (item == 'double') {
                has_double_children = true;
            } else if (item == 'black') {
                is_black_list = true;
            }
        });
        return [tt_id, tt_par_id, has_children, has_double_children, is_black_list];
    }

    var old_rows = {}, indent = 16, prev_icon, prev_indent;
    var expanded_parents = [];
    table.find('tr').each(function() {
        var tt_par_id, tt_id, has_children, has_double_children, is_black_list,
            new_element = $('<div>', {class: 'tabletree'}), curr_ids = get_ids($(this).attr('class')),
            tree_cell = $(this).children('td:nth-child(' + column + ')');
        tt_id = curr_ids[0];
        tt_par_id = curr_ids[1];
        has_children = curr_ids[2];
        has_double_children = curr_ids[3];
        is_black_list = curr_ids[4];

        if (!tt_id) {
            return;
        }
        var curr_indent = 0, exists = false;
        if ($(this).find('.tabletree').length) {
            curr_indent = parseInt(tree_cell.find('.tabletree').css('margin-left'), 10);
            exists = true;
        }
        else {
            if (tt_par_id && tt_par_id in old_rows) {
                curr_indent = old_rows[tt_par_id] + indent;
            }
            new_element.append($("<span>", {style: 'margin-left: ' + curr_indent + 'px;', class: 'tabletree'}));
            if ($(this).hasClass('tr-show') || has_double_children) {
                $(this).removeClass('tr-show');
                if (!is_black_list) {
                    new_element.append($('<i>', {class: expanded, style: 'cursor: pointer', id: 'tt_expander_' + tt_id}));
                }
                expanded_parents.push(tt_id);
            }
            else {
                if (!is_black_list) {
                    new_element.append($('<i>', {class: collapsed, style: 'cursor: pointer', id: 'tt_expander_' + tt_id}));
                }
            }
            tree_cell.prepend(new_element.html());
            if (tt_par_id && expanded_parents.indexOf(tt_par_id) === -1) {
                $(this).hide();
            }
        }
        old_rows[tt_id] = curr_indent;
        if (prev_icon) {
            if (prev_indent >= curr_indent) {
                prev_icon.attr('style', 'opacity:0;');
            }
            else {
                prev_icon.attr('style', 'opacity:100%;');
            }
        }
        prev_icon = tree_cell.find('i');
        prev_indent = curr_indent;

        if (!exists) {
            $('#tt_expander_' + tt_id).click(function () {
                var prev_ids = [tt_id], next_tr = $(this).closest('tr').next('tr'),
                    next_ids, next_id, next_par_id;
                if ($(this).attr('class') === expanded) {
                    $(this).attr('class', collapsed);
                    while (true) {
                        if (!next_tr.length) {
                            update_colors(table);
                            return;
                        }
                        next_ids = get_ids(next_tr.attr('class'));
                        next_id = next_ids[0];
                        next_par_id = next_ids[1];
                        if (!next_id) {
                            update_colors(table);
                            return;
                        }
                        if (next_par_id && prev_ids.indexOf(next_par_id) >= 0) {
                            next_tr.hide();
                            prev_ids.push(next_id);
                        }
                        else {
                            update_colors(table);
                            return;
                        }
                        next_tr = next_tr.next('tr');
                    }
                }
                else if ($(this).attr('class') === collapsed) {
                    $(this).attr('class', expanded);
                    while (true) {
                        if (!next_tr.length) {
                            update_colors(table);
                            return;
                        }
                        next_ids = get_ids(next_tr.attr('class'));
                        next_id = next_ids[0];
                        next_par_id = next_ids[1];
                        if (!next_id) {
                            update_colors(table);
                            return;
                        }
                        if (next_par_id && prev_ids.indexOf(next_par_id) >= 0) {
                            next_tr.show();
                            if (next_tr.find('i').first().attr('class') === expanded) {
                                prev_ids.push(next_id);
                            }
                        }
                        next_tr = next_tr.next('tr');
                    }
                }
            });
        }
    });
    if (prev_icon) {
        prev_icon.attr('style', 'opacity:0;');
    }
};
