.. _fr-label_field_style:

=====================
Label and field style
=====================

This feature allows the user to change the style of the labels and
fields (form/tree).

There are 2 ways to do that:

    * Add keywords to the states via view_attributes (static to one view).
      Only the fields/labels changed are affected.

    * Add keywords to the states via the fields in the model (dynamic to all views).
      All the fields/labels are affected.

More there are 4 places:

    * The fields from the form

    * The fields from the tree

    * The labels from the form

    * The labels from the tree


Keywords
--------

Format: [type_]style_value = [pyson] or True/False
If the result of the pyson is True, the format is applied.

type:

   * (`label`) Only for the labels

   * (`field`) Only for the fields

The type is used only for those 2 specific cases:

   * The dynamic way. Apply the keyword to all targets (label/field)
     or specify one with a type.

   * The static way. Normally we don't need a type but for the label
     from a tree, there is no label in the xml. So we need to use
     the field with a type for the keywords.

style/value:

    * (`color`) Change the color of the text /
      the value is the string of the color (`red`)

    * (`fg`) Change the color of the foreground /
      the value is the string of the color (`red`)

    * (`bg`)           "             background /
                       "                   (`red`)

    * (`font`) Change the style of the text /
      The value is the style string (`courier bold 20`)

For the labels the choice of the color is limited to red, green,
blue, turquoise, gray, brown, maroon, violet, purple, yellow,
pink, beige, white, black.
If you want more color you can add it in the dict COLOR_RGB
(tryton/tryton/commom/commom.py).


Via view_attributes (limited to one view)
-----------------------------------------

You can add keywords in the states via view_attributes.
This way is used to specify an attribute for a field or a label.

Example:

return super(Party, cls).view_attributes() + [
            ('/form/group[@id="name"]/field...', 'states',
            {'invisible': True,
            'font_courier bold 20': Eval('is_person'),
            'color_red': Eval('is_person'),
            'fg_blue': Eval('is_person')}),
            ]


Via the fiels in the model (dynamic to all views)
-------------------------------------------------

You can add keywords in the states at the creation of the field in the class.
This way is used to specify an attribute for the field and
his label (the linked one).
It's not working for the labels from the tree.

Example:

birth_name = fields.Char('Birth Name', states={
            'invisible': ~STATES_PERSON,
            'label_font_courier bold 20': Eval('is_person'),
            'field_color_red': Eval('is_person')
            }, depends=['is_person'])
