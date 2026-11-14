package Corpus::Report;
use strict;
use warnings;
use JSON::PP;
use TAP::Parser;

# Framing belongs to this finite pgTAP family; TAP syntax belongs to TAP::Parser.
sub parse_stream {
    my ($tap) = @_;
    my $parser = TAP::Parser->new({tap => $tap});
    my @results;
    while (my $result = $parser->next) { push @results, $result }
    return ($parser, \@results);
}

sub check_parser {
    my ($parser, $results, $count, $errors, $label) = @_;
    push @$errors, "$label: $_" for $parser->parse_errors;
    push @$errors, "$label: assertion count differs from declared $count"
        if $parser->tests_run != $count || !defined($parser->tests_planned)
            || $parser->tests_planned != $count;
    for my $result (@$results) {
        push @$errors, "$label: bailout" if $result->is_bailout;
        push @$errors, "$label: unexpected TAP line: " . $result->raw if $result->is_unknown;
        push @$errors, "$label: TODO/SKIP is not execution"
            if ($result->is_test || $result->is_plan) && $result->has_directive;
    }
}

sub analyze {
    my ($raw, $manifest, $process) = @_;
    my @errors;
    my %expected = map { $_->{name} => $_ } @{$manifest->{cases}};
    my (%seen, %observed);
    my ($active, @child, @outer, $context);
    for my $line (split /\n/, $raw) {
        if ($line =~ /^# CORPUS_CONTEXT (.+)$/) {
            push @errors, 'duplicate session context' if defined $context;
            eval { $context = decode_json($1) };
            push @errors, 'malformed session context' if $@;
            push @outer, $line;
        } elsif ($line =~ /^# Subtest: (.+)\(\)$/) {
            push @errors, 'unfinished child before next case' if defined $active;
            $active = $1;
            @child = ();
            push @errors, "unknown case: $active" unless exists $expected{$active};
            push @errors, "duplicate case: $active" if $seen{$active}++;
            push @outer, $line;
        } elsif ($line =~ /^    (.*)$/) {
            push @errors, 'child stream outside a case' unless defined $active;
            my $child = $1;
            push @errors, 'nested subtest framing' if $child =~ /^(?:\s|# Subtest:)/;
            push @child, $child;
        } else {
            push @outer, $line;
            my ($parser, $results) = parse_stream($line . "\n");
            my @tests = grep { $_->is_test } @$results;
            if (@tests) {
                my $result = $tests[0];
                my $name = $result->description;
                $name =~ s/^-\s*//;
                if (!defined($active) || $name ne $active) {
                    push @errors, "outer case does not match child: $name";
                } else {
                    my ($child_parser, $child_results) = parse_stream(join("\n", @child) . "\n");
                    my @case_errors;
                    check_parser($child_parser, $child_results,
                        exists($expected{$name}) ? $expected{$name}{assertions} : -1,
                        \@case_errors, $name);
                    push @case_errors, "$name: failed assertion" if $child_parser->failed;
                    push @case_errors, "$name: failed outer result" unless $result->is_ok;
                    push @case_errors, "$name: TODO/SKIP outer result" if $result->has_directive;
                    $observed{$name} = {name => $name, status => @case_errors ? 'failed' : 'passed',
                        assertions => $child_parser->tests_run, errors => \@case_errors};
                    push @errors, @case_errors;
                }
                undef $active;
                @child = ();
            }
        }
    }
    push @errors, 'truncated child stream' if defined $active;
    my ($outer_parser, $outer_results) = parse_stream(join("\n", @outer) . "\n");
    check_parser($outer_parser, $outer_results, scalar(keys %expected), \@errors, 'batch');
    push @errors, 'outer assertion failed' if $outer_parser->failed;
    push @errors, 'missing session context' unless ref($context) eq 'HASH';
    push @errors, 'psql did not exit successfully'
        if !defined($process->{exit}) || $process->{exit} != 0 || $process->{wait} != 0;
    push @errors, "missing case: $_" for grep { !exists $observed{$_} } sort keys %expected;
    return {schema => 'pgtap-batch/v1', valid => @errors ? JSON::PP::false : JSON::PP::true,
        errors => \@errors, observed => \%observed, context => $context, process => $process};
}
1;
