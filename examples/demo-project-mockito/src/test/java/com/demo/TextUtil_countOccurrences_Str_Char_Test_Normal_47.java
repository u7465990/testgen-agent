package com.demo;

import com.demo.TextUtil;
import org.junit.Assert;
import org.junit.Test;

public class TextUtil_countOccurrences_Str_Char_Test_Normal_47 {


    @Test
    public void testCountOccurrencesWithRepresentativeInputs() {
        int resultTest = TextUtil.countOccurrences("test", 'a');
        Assert.assertEquals(0, resultTest);

        int resultEmpty = TextUtil.countOccurrences("", 'a');
        Assert.assertEquals(0, resultEmpty);

        int resultMatch = TextUtil.countOccurrences("banana", 'a');
        Assert.assertEquals(3, resultMatch);
    }

}
