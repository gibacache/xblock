
# Imports ###########################################################

import logging

from xblock.fields import List, Scope, Boolean, String
from xblock.validation import ValidationMessage
from .questionnaire import QuestionnaireAbstractBlock
from xblockutils.resources import ResourceLoader


# Globals ###########################################################

log = logging.getLogger(__name__)


# Make '_' a no-op so we can scrape strings
def _(text):
    return text

# Classes ###########################################################


class ArgumentativeBlock(QuestionnaireAbstractBlock):
    """
    An XBlock used to ask multiple-response questions
    """
    CATEGORY = 'pb-arg'
    STUDIO_LABEL = _(u"Argumentative Question")

    student_choices = List(
        # Last submissions by the student
        default=[],
        scope=Scope.user_state
    )
    required_choices = List(
        display_name=_("Required Choices"),
        help=_("Specify the value[s] that students must select for this MRQ to be considered correct."),
        scope=Scope.content,
        list_values_provider=QuestionnaireAbstractBlock.choice_values_provider,
        list_style='set',  # Underered, unique items. Affects the UI editor.
        default=[],
    )
    ignored_choices = List(
        display_name=_("Ignored Choices"),
        help=_(
            "Specify the value[s] that are neither correct nor incorrect. "
            "Any values not listed as required or ignored will be considered wrong."
        ),
        scope=Scope.content,
        list_values_provider=QuestionnaireAbstractBlock.choice_values_provider,
        list_style='set',  # Underered, unique items. Affects the UI editor.
        default=[],
    )
    message = String(
        display_name=_("Message"),
        help=_("General feedback provided when submitting"),
        scope=Scope.content,
        default=""
    )
    hide_results = Boolean(display_name="Hide results", scope=Scope.content, default=False)
    editable_fields = (
        'question', 'required_choices', 'ignored_choices', 'message', 'display_name',
        'show_title', 'weight', 'hide_results',
    )

    def describe_choice_correctness(self, choice_value):
        if choice_value in self.required_choices:
            return self._(u"Required")
        elif choice_value in self.ignored_choices:
            return self._(u"Ignored")
        return self._(u"Not Acceptable")

    def get_results(self, previous_result):
        """
        Get the results a student has already submitted.
        """
        result = self.calculate_results(previous_result['submissions'])
        result['completed'] = True
        return result

    def get_last_result(self):
        if self.student_choices:
            return self.get_results({'submissions': self.student_choices})
        else:
            return {}

    def submit(self, submissions):
        log.debug(u'Received MRQ submissions: "%s"', submissions)

        result = self.calculate_results(submissions)
        self.student_choices = submissions

        log.debug(u'MRQ submissions result: %s', result)
        return result

    def calculate_results(self, submissions):
        score = 0
        results = []

        for choice in self.custom_choices:
            choice_completed = True
            choice_tips_html = []
            choice_selected = choice.value in submissions

            if choice.value in self.required_choices:
                if not choice_selected:
                    choice_completed = False
            elif choice_selected and choice.value not in self.ignored_choices:
                choice_completed = False
            for tip in self.get_tips():
                if choice.value in tip.values:
                    choice_tips_html.append(tip.render('mentoring_view').content)

            if choice_completed:
                score += 1

            choice_result = {
                'value': choice.value,
                'selected': choice_selected,
                }
            # Only include tips/results in returned response if we want to display them
            if not self.hide_results:
                loader = ResourceLoader(__name__)
                choice_result['completed'] = choice_completed
                choice_result['tips'] = loader.render_template('templates/html/tip_choice_group.html', {
                    'tips_html': choice_tips_html,
                    })

            results.append(choice_result)

        status = 'incorrect' if score <= 0 else 'correct' if score >= len(results) else 'partial'

        return {
            'submissions': submissions,
            'status': status,
            'choices': results,
            'message': self.message_formatted,
            'weight': self.weight,
            'score': (float(score) / len(results)) if results else 0,
        }

    def validate_field_data(self, validation, data):
        """
        Validate this block's field data.
        """
        super(ArgumentativeBlock, self).validate_field_data(validation, data)

        def add_error(msg):
            validation.add(ValidationMessage(ValidationMessage.ERROR, msg))

        def choice_name(choice_value):
            for choice in self.human_readable_choices:
                if choice["value"] == choice_value:
                    return choice["display_name"]
            return choice_value

        all_values = set(self.all_choice_values)
        required = set(data.required_choices)
        ignored = set(data.ignored_choices)

        if len(required) < len(data.required_choices):
            add_error(self._(u"Duplicate required choices set"))
        if len(ignored) < len(data.ignored_choices):
            add_error(self._(u"Duplicate ignored choices set"))
        for val in required.intersection(ignored):
            add_error(self._(u"A choice is listed as both required and ignored: {}").format(choice_name(val)))
        for val in (required - all_values):
            add_error(self._(u"A choice value listed as required does not exist: {}").format(choice_name(val)))
        for val in (ignored - all_values):
            add_error(self._(u"A choice value listed as ignored does not exist: {}").format(choice_name(val)))
